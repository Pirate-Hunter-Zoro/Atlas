"""The machine's tools, as the tree declares them, and what became of them.

Four layers, each found in the tree and never in a list. The board server runs
none of them: `scripts/setup.sh` installs, `scripts/tools.sh` reads
descriptors, and upkeep, through Atlas's hook (`scripts/brew-upgrade.py`),
keeps them current.

  BREWFILES    the root `Brewfile` plus each subject's own, as one sorted and
               deduplicated union (`union_text`). setup.sh bundles it with
               --no-upgrade and upkeep installs it, from
               `~/.local/state/atlas-setup/Brewfile.all`, rewritten only when
               it changes (`write_union`). brew bundle runs that file as Ruby,
               so only a bare `tap "x"`, `brew "x"` or `cask "x"` whose name
               passes `name_problem` gets in, rebuilt from the name; any other
               line is refused (`checked`) and kept in tools.json
               `refused_brew`. A tap, or an `owner/repo/formula` name, needs
               its `owner/repo` in the root `Brewfile.taps`. An entry that
               leaves the union is remembered in tools.json `left_brew`,
               unless upkeep/Brewfile declares it; nothing is uninstalled.
  MISE         a subject's and Atlas's own `mise.toml` and `mise.lock` pin
               their toolchains. `marker_dirs` finds a marker at a subject's
               root and one directory down, skipping SKIP. Atlas's root is not
               a subject, so `root_mise` and `root_mise_tools` read it for
               setup.sh and the upkeep hook only.
  DESCRIPTORS  `<subject>/tools/<name>.sh`, read by scripts/tools.sh. One name
               in two subjects must be the same bytes (`descriptors`).
  DECLARED     `declare` writes one tool into the repository's own files: a
               `brew` or `cask` line in the root or a subject's Brewfile, or a
               `[tools]` entry in the root or a subject's mise.toml. Every
               string it writes is checked first: the name, the version and
               the one-line `--why` (`clean_why`), and so is every mise config
               mise reads where the pin goes (`mise_chain_problem`). setup.sh
               and the upkeep hook install what those files declare, so a
               declaration made on one Mac reaches every clone through git.
               Nothing is uninstalled.

State is tools.json in the board's state directory: one record per tool
tools.sh has handled, `left` for one no longer declared, `left_brew`, and
`refused_brew`, `pins`, the mise pins the hook found behind, which brief.py puts in
that subject's sessions as a bump to propose. `python3 -m
tutorboard.toolplan` is tools.sh's and setup.sh's way in. Stdlib only, and
3.7-clean.
"""

import fcntl
import hashlib
import json
import os
import re
import sys
from datetime import datetime

# A marker's lockfile, which must sit beside it. build.zig.zon is its own:
# it carries each dependency's content hash, and Zig writes no other lock.
MARKERS = (("mise.toml", "mise.lock"), ("Cargo.toml", "Cargo.lock"),
           ("pubspec.yaml", "pubspec.lock"), ("build.zig.zon", "build.zig.zon"))
# Never looked into for a marker: build output, caches and environments.
SKIP = ("target", "build", ".dart_tool", ".venv", "node_modules",
        "zig-out", ".zig-cache", "zig-pkg")
# A Brewfile's entries, in the order brew bundle needs them: a tap first.
KINDS = ("tap", "brew", "cask", "mas", "whalebrew", "vscode")
# A brew or cask name, and each half of a tap's owner/repo.
NAME = re.compile(r"^[a-z0-9][a-z0-9+._@-]*\Z")
# The one line shape that reaches Brewfile.all.
BARE = re.compile(r'^(tap|brew|cask) "([^"\\]*)"\Z')
# The taps a Brewfile may name, one owner/repo a line, at Atlas's root.
TAPS_FILE = "Brewfile.taps"
# `checked`'s line for a Brewfile refused whole.
WHOLE_FILE = "(the whole file)"


def state_dir():
    return os.environ.get("BOARD_STATE_DIR") or os.path.join(
        os.path.expanduser("~"), ".local", "state", "tutor-board")


def setup_dir():
    return os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "state"), "atlas-setup")


def union_path():
    return os.path.join(setup_dir(), "Brewfile.all")


def tools_path(where=None):
    return os.path.join(where or state_dir(), "tools.json")


def now_stamp():
    return datetime.now().replace(microsecond=0).isoformat()


def subjects_of(base):
    """[(id, root)] of every subject under `base`."""
    from . import subjects                                   # local: light import
    return [(s[0] + "/" + s[2], s[3]) for s in subjects.walk(base)]


# ------------------------------------------------------------------ markers

def marker_dirs(root, name):
    """The directories, `root` and one level down, that hold the file `name`.
    A dot directory and SKIP are never entered."""
    out = []
    if os.path.isfile(os.path.join(root, name)):
        out.append(root)
    try:
        kids = sorted(os.listdir(root))
    except OSError:
        kids = []
    for kid in kids:
        where = os.path.join(root, kid)
        if kid.startswith(".") or kid in SKIP or not os.path.isdir(where):
            continue
        if os.path.isfile(os.path.join(where, name)):
            out.append(where)
    return out


def markers(root):
    """[(marker, lockfile, dir)] for every MARKERS marker in `root` and one
    directory down."""
    out = []
    for marker, lock in MARKERS:
        for d in marker_dirs(root, marker):
            out.append((marker, lock, d))
    return out


def mise_dirs(base):
    """[(subject id, dir)] of every directory holding a mise.toml."""
    out = []
    for ident, root in subjects_of(base):
        for d in marker_dirs(root, "mise.toml"):
            out.append((ident if d == root else ident + "/" + os.path.basename(d), d))
    return out


def pinned_in(d):
    """The tool names `d`'s own mise.toml pins, sorted: the keys of its
    `[tools]` table and the names of its `[tools.<name>]` tables. What
    `mise install --locked` is named in `d`, so a tool the owner's global
    config adds (which has no entry in the subject's mise.lock, and fails
    --locked) is never installed from here."""
    names = set()
    try:
        with open(os.path.join(d, "mise.toml"), encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    inside = False
    for raw in lines:
        line = _strip_comment(raw).strip()
        if line.startswith("["):
            head = line.strip("[] ").replace(" ", "")
            inside = head == "tools"
            if head.startswith("tools."):
                names.add(head[6:].strip("\"'"))
            continue
        if inside and "=" in line:
            key = line.split("=", 1)[0].strip().strip("\"'")
            if key:
                names.add(key)
    return sorted(names)


def mise_tools(base):
    """The tool names every mise.toml under `base` pins, sorted: the only
    tools brew-upgrade.py's `mise prune --tools` may touch."""
    names = set()
    for _ident, d in mise_dirs(base):
        names.update(pinned_in(d))
    return sorted(names)


def root_mise(base):
    """(mise.toml, mise.lock) at Atlas's own root, whether or not either
    exists. Atlas's root is not a subject: only setup.sh and the hook read
    it, through this helper."""
    return (os.path.join(base, "mise.toml"), os.path.join(base, "mise.lock"))


def _toml_tools(path):
    """[(name, version)] of `path`'s `[tools]` table, simple
    `name = "version"` entries only, in file order."""
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return out
    inside = False
    for raw in lines:
        line = _strip_comment(raw).strip()
        if line.startswith("["):
            inside = line.strip("[] ").replace(" ", "") == "tools"
            continue
        if inside and "=" in line:
            key, value = line.split("=", 1)
            key = key.strip().strip("\"'")
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            elif value.startswith("{") and value.endswith("}"):
                m = re.search(r'version\s*=\s*"([^"]*)"', value)
                if m:
                    value = m.group(1)
            if key:
                out.append((key, value))
    return out


def root_mise_tools(base):
    """The (name, version) pairs Atlas's own mise.toml pins, in file order."""
    return _toml_tools(root_mise(base)[0])


# ----------------------------------------------------------------- Brewfile

def _strip_comment(line):
    """`line` without a trailing `# ...` that sits outside quotes."""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#":
            return line[:i]
    return line


def read_entries(path):
    """(entries, problem) of one Brewfile: its lines with comments and blank
    lines dropped and whitespace collapsed, and "" -- or ([], why) when it
    cannot be read or is not UTF-8."""
    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read().splitlines()
    except UnicodeDecodeError:
        return [], "not UTF-8, so none of it is read"
    except OSError as e:
        return [], "cannot be read (%s)" % (e.strerror or "error")
    out = []
    for line in raw:
        line = " ".join(_strip_comment(line).split())
        if line:
            out.append(line)
    return out, ""


def entries(path):
    """The entries of one Brewfile (`read_entries`); [] when it cannot be
    read."""
    return read_entries(path)[0]


def _kind(entry):
    word = entry.split(None, 1)[0]
    return KINDS.index(word) if word in KINDS else len(KINDS)


def brewfiles(base):
    """[(label, path)]: the root Brewfile, then each subject's."""
    out = []
    root = os.path.join(base, "Brewfile")
    if os.path.isfile(root):
        out.append(("Brewfile", root))
    for ident, where in subjects_of(base):
        bf = os.path.join(where, "Brewfile")
        if os.path.isfile(bf):
            out.append((ident + "/Brewfile", bf))
    return out


def allowed_taps(base):
    """The taps `base/Brewfile.taps` lists: one `owner/repo` a line, `#`
    comments and any other line skipped. Empty when the file is missing."""
    out = set()
    try:
        with open(os.path.join(base, TAPS_FILE), encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return out
    for raw in lines:
        tap = raw.split("#", 1)[0].strip()
        if _tap_shape(tap):
            out.add(tap)
    return out


def _tap_shape(tap):
    parts = tap.split("/")
    return len(parts) == 2 and all(NAME.match(p) for p in parts)


def name_problem(kind, name, taps):
    """Why `name` cannot be a `kind` (tap, brew or cask) entry, or "" when it
    can. A brew or cask is a NAME, or `owner/repo/<NAME>` from an allowed
    tap; a tap is an allowed `owner/repo`. `taps` is `allowed_taps`."""
    if kind == "tap":
        if not _tap_shape(name):
            return "a tap is owner/repo in lower case"
        return "" if name in taps else "tap %s is not in %s" % (name, TAPS_FILE)
    parts = name.split("/")
    if len(parts) == 1 and NAME.match(name):
        return ""
    if len(parts) == 3 and all(NAME.match(p) for p in parts):
        tap = parts[0] + "/" + parts[1]
        return "" if tap in taps else "tap %s is not in %s" % (tap, TAPS_FILE)
    return "a %s name is lower-case letters, digits and + . _ @ -" % kind


def checked(base):
    """(sorted unique entries, [labels], refused) over every Brewfile. An
    entry is rebuilt as `<kind> "<name>"` from a bare tap, brew or cask line
    whose name passes `name_problem`, so nothing else reaches Brewfile.all.
    `refused` is [(label, line, why)] for every other line but a comment or
    a blank one, which are dropped, and one (label, WHOLE_FILE, why) for a
    Brewfile that cannot be read or is not UTF-8."""
    taps = allowed_taps(base)
    seen = set()
    labels = []
    refused = []
    for label, path in brewfiles(base):
        labels.append(label)
        lines, problem = read_entries(path)
        if problem:
            refused.append((label, WHOLE_FILE, problem))
        for line in lines:
            m = BARE.match(line)
            if not m:
                refused.append((label, line, "not a bare tap, brew or cask line"))
                continue
            why = name_problem(m.group(1), m.group(2), taps)
            if why:
                refused.append((label, line, why))
                continue
            seen.add('%s "%s"' % (m.group(1), m.group(2)))
    return sorted(seen, key=lambda e: (_kind(e), e)), labels, refused


def union(base):
    """(sorted unique entries, [labels]) over every Brewfile, refused lines
    left out (`checked`)."""
    got, labels, _refused = checked(base)
    return got, labels


def _printable(text):
    """`text` with every character Python cannot print, a line break among
    them, as `?`: safe inside a `#` comment."""
    return "".join(c if c.isprintable() else "?" for c in text)


def union_text(base):
    got, labels = union(base)
    head = ("# Written by scripts/setup.sh and Atlas's upkeep hook; edit the "
            "Brewfiles it joins:\n# %s\n"
            % _printable(", ".join(labels or ["(none)"])))
    return head + "".join(e + "\n" for e in got)


def machine_entries(base):
    """The entries of `upkeep/Brewfile`, which upkeep installs on every
    machine whatever Atlas declares."""
    return set(entries(os.path.join(base, "upkeep", "Brewfile")))


def write_union(base, dest=None):
    """Write the union to `dest` (Brewfile.all) when it differs. (changed,
    path). tools.json `refused_brew` is set to the lines `checked` refused,
    as [{file, line, why}]. An entry that left it goes into tools.json `left_brew`, and one
    that came back comes out. An entry upkeep/Brewfile declares never counts
    as left: upkeep keeps it installed."""
    dest = dest or union_path()
    text = union_text(base)
    refused = [{"file": label, "line": line, "why": why}
               for label, line, why in checked(base)[2]]

    def note_refused(doc):
        if refused:
            doc["refused_brew"] = refused
        else:
            doc.pop("refused_brew", None)
    if (read().get("refused_brew") or []) != refused:
        update(note_refused)
    machine = machine_entries(base)
    if set(read().get("left_brew") or {}) & machine:
        def drop(doc):
            for e in machine:
                doc.setdefault("left_brew", {}).pop(e, None)
        update(drop)
    try:
        with open(dest, encoding="utf-8") as fh:
            old = fh.read()
    except OSError:
        old = None
    if old == text:
        return False, dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, dest)
    before = set(l for l in (old or "").splitlines() if l and not l.startswith("#"))
    now = set(l for l in text.splitlines() if l and not l.startswith("#"))
    back = now | machine
    gone = before - back

    def change(doc):
        left = doc.setdefault("left_brew", {})
        for e in back:
            left.pop(e, None)
        for e in gone:
            left.setdefault(e, now_stamp())
    if gone or (set(read().get("left_brew") or {}) & back):
        update(change)
    return True, dest


def brew_installed(entry, prefix):
    """Where a `brew` or `cask` entry is installed under `prefix`, or None."""
    m = re.match(r'^(brew|cask)\s+"([^"]+)"', entry)
    if not m or not prefix:
        return None
    name = m.group(2).rsplit("/", 1)[-1]
    where = os.path.join(prefix, "Cellar" if m.group(1) == "brew" else "Caskroom", name)
    return where if os.path.isdir(where) else None


# -------------------------------------------------------------- descriptors

def descriptors(base):
    """(plan, conflicts). `plan` is [{name, path, subjects}] sorted by name,
    one per name whose every copy is the same bytes; `conflicts` is
    [{name, paths}] for a name whose copies differ, which is in no plan."""
    found = {}
    for ident, root in subjects_of(base):
        d = os.path.join(root, "tools")
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        for fn in names:
            path = os.path.join(d, fn)
            if not fn.endswith(".sh") or fn.startswith(".") or not os.path.isfile(path):
                continue
            try:
                with open(path, "rb") as fh:
                    digest = hashlib.sha1(fh.read()).hexdigest()
            except OSError:
                continue
            found.setdefault(fn[:-3], []).append((ident, path, digest))
    plan, conflicts = [], []
    for name in sorted(found):
        copies = found[name]
        if len(set(c[2] for c in copies)) > 1:
            conflicts.append({"name": name, "paths": [c[1] for c in copies]})
        else:
            plan.append({"name": name, "path": copies[0][1],
                         "subjects": [c[0] for c in copies]})
    return plan, conflicts


# -------------------------------------------------------------------- state

def read(where=None):
    """tools.json as a dict; {} when missing or broken."""
    try:
        with open(tools_path(where), encoding="utf-8") as fh:
            got = json.load(fh)
        return got if isinstance(got, dict) else {}
    except (OSError, ValueError):
        return {}


def update(change, where=None):
    """Read tools.json, apply `change(doc)` under a lock, and write it back
    only when it differs. True when it was written."""
    path = tools_path(where)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path + ".lock", os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        doc = read(where)
        before = json.dumps(doc, sort_keys=True)
        change(doc)
        after = json.dumps(doc, sort_keys=True)
        if after == before:
            return False
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
        return True
    finally:
        os.close(fd)


def record(base, rows, where=None):
    """Fold tools.sh's result rows into tools.json. A row is a dict with
    name, event (present, installed, updated, current, manual, checked or
    failed), step (install, update or check), version, found, bin, dir,
    every_days, stale_days and why. `updated` is the last install or update
    that worked, `attempted` the last update tried, `failed` the last failure
    until its step next works. `manual` is a tool with no T_UPDATE: it is
    never a failure, its T_MANUAL is kept in `manual`, and a version that
    moved since the last row counts as updated, so it goes stale only when
    the owner leaves it. A tool that is no longer declared anywhere moves
    from `tools` to `left`; `conflicts` is rewritten from the tree."""
    plan, conflicts = descriptors(base)
    declared = set(p["name"] for p in plan) | set(c["name"] for c in conflicts)
    stamp = now_stamp()

    def change(doc):
        tools = doc.setdefault("tools", {})
        left = doc.setdefault("left", {})
        for row in rows:
            name = row["name"]
            rec = tools.setdefault(name, {"seen": stamp})
            left.pop(name, None)
            was = rec.get("version")
            for k in ("bin", "dir", "found", "version"):
                if row.get(k):
                    rec[k] = row[k]
            for k in ("every_days", "stale_days"):
                try:
                    rec[k] = int(row.get(k))
                except (TypeError, ValueError):
                    pass
            ev, step = row.get("event"), row.get("step") or ""
            if ev in ("installed", "updated", "current"):
                rec["updated"] = stamp
                rec.pop("failed", None)
                rec.pop("failed_step", None)
            if ev in ("updated", "current", "manual") or \
                    (ev == "failed" and step == "update"):
                rec["attempted"] = stamp
            if ev == "manual":
                rec["manual"] = row.get("why") or "by hand"
                if was and row.get("version") and row["version"] != was:
                    rec["updated"] = stamp
                if rec.get("failed_step") == "update":
                    rec.pop("failed", None)
                    rec.pop("failed_step", None)
            elif ev in ("updated", "current"):
                rec.pop("manual", None)
            if ev == "failed":
                rec["failed"] = row.get("why") or "failed"
                rec["failed_step"] = step
            elif (ev == "checked" and rec.get("failed_step") == "check") or \
                    (ev == "present" and rec.get("failed_step") == "install"):
                rec.pop("failed", None)
                rec.pop("failed_step", None)
        for name in list(tools):
            if name not in declared:
                rec = tools.pop(name)
                left[name] = {"dir": rec.get("dir") or os.path.dirname(rec.get("found") or ""),
                              "bin": rec.get("bin") or name, "since": stamp}
        if not left:
            doc.pop("left")
        doc["conflicts"] = [{"name": c["name"], "paths": [
            os.path.relpath(p, base) for p in c["paths"]]} for c in conflicts]
        if not doc["conflicts"]:
            doc.pop("conflicts")
    return update(change, where)


def write_pins(pins, where=None):
    """Set tools.json `pins` to [{subject, tool, pinned, latest, dir}]."""
    def change(doc):
        if pins:
            doc["pins"] = pins
        else:
            doc.pop("pins", None)
    return update(change, where)


def pins_of(said, subject, where=None):
    """[{subject, tool, pinned, latest}] from `mise outdated --json --bump
    --local` run in `where` (kept as `dir`, which a session's brief
    matches). mise 2026.10 prints an object keyed by tool, each record
    {name, requested, current, bump, latest, release_url?, source: {type,
    path}}, and lists every configured tool, installed or not. `bump` is
    the request `mise upgrade --bump` would write, null when the request
    already reaches the newest release (an exact pin at it, a bare major,
    `latest`), so a pin is behind exactly when `bump` is set. `latest` is
    the newest release. A record whose source is another directory's
    config (a parent subject's, seen from one directory down) is that
    directory's to report."""
    try:
        data = json.loads(said or "{}")
    except ValueError:
        return []
    if not isinstance(data, dict):
        return []
    here = os.path.realpath(where) if where else None
    out = []
    for key, r in sorted(data.items()):
        if not isinstance(r, dict):
            continue
        src = r.get("source") if isinstance(r.get("source"), dict) else {}
        if here and src.get("path") and \
                os.path.realpath(os.path.dirname(str(src["path"]))) != here:
            continue
        name = r.get("name") or key
        pinned, bump = r.get("requested"), r.get("bump")
        latest = r.get("latest") or bump
        if not (name and pinned and bump) or str(bump) == str(pinned):
            continue
        pin = {"subject": subject, "tool": str(name), "pinned": str(pinned),
               "latest": str(latest)}
        if where:
            pin["dir"] = where
        out.append(pin)
    return out


# ------------------------------------------------------------- declarations

BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+\Z")
# mise backends a declaration may name, as `<backend>:<package>`. Not asdf,
# vfox or http: their plugins or URLs are code from anywhere.
BACKENDS = ("aqua", "cargo", "dotnet", "gem", "github", "gitlab", "go", "npm",
            "pipx", "spm", "ubi")
PACKAGE = re.compile(r"^[A-Za-z0-9@][A-Za-z0-9+._@/-]*\Z")
VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+._:-]*\Z")
# What a mise config may hold for `declare` to write beside it, line by
# line: min_version at the top, then [tools] and [tools.<name>] tables whose
# entries are versions. A tool option outside TOOL_OPTIONS (postinstall,
# install_env, ...) runs code or sets the environment, and so does every
# other table ([env], [hooks], [tasks]).
MISE_TOP = ("min_version",)
TOOL_OPTIONS = ("version", "os")
# What a string value may hold. mise renders every value as a tera template,
# so `{{ exec(...) }}` would run; no brace, %, #, $, paren, quote or
# backslash can be in one.
_SAFE = r"[A-Za-z0-9 +._:@/<>=~^,!-]"
_STR = r'(?:"%s*"|\'%s*\')' % (_SAFE, _SAFE)
_ARR = r'\[\s*(?:%s\s*(?:,\s*%s\s*)*,?\s*)?\]' % (_STR, _STR)
_KEY = r'(?:[A-Za-z0-9_-]+|"[^"\\\n]*"|\'[^\'\n]*\')'
MISE_HEAD = re.compile(r"^\[\s*(%s)(?:\s*\.\s*(%s))?\s*\]\Z" % (_KEY, _KEY))
MISE_PAIR = re.compile(r"^(%s)\s*=\s*(.*?)\Z" % _KEY)
MISE_STR = re.compile(r"^%s\Z" % _STR)
MISE_ARR = re.compile(r"^%s\Z" % _ARR)
_PAIR = r"[A-Za-z_]+\s*=\s*(?:%s|%s)" % (_STR, _ARR)
MISE_INLINE = re.compile(r"^\{\s*(?:%s(?:\s*,\s*%s)*)?\s*\}\Z" % (_PAIR, _PAIR))
MISE_INLINE_PAIR = re.compile(r"([A-Za-z_]+)\s*=\s*(%s|%s)" % (_STR, _ARR))
WHY_MAX = 120


def clean_why(why):
    """`why` as one comment line: every whitespace run one space, quotes,
    backslashes and any character Python cannot print dropped, at most
    WHY_MAX characters. Nothing in it can end a Ruby or TOML comment."""
    text = " ".join(str(why or "").split())
    text = "".join(c for c in text if c.isprintable() and c not in "\"'`\\")
    return " ".join(text.split())[:WHY_MAX].strip()


def mise_name_problem(name):
    """Why `name` cannot be a mise tool, or "": a bare key (`python`), or
    `<backend>:<package>` with the backend in BACKENDS."""
    if BARE_KEY.match(name):
        return ""
    backend, colon, package = name.partition(":")
    if colon and backend in BACKENDS and PACKAGE.match(package):
        return ""
    if colon and BARE_KEY.match(backend) and backend not in BACKENDS:
        return "mise backend %s is not one of %s" % (backend, ", ".join(BACKENDS))
    return ("a mise tool is a bare key, or <backend>:<package> of letters, digits "
            "and + . _ @ / -")


def mise_version_problem(version):
    if VERSION.match(version) and not version.startswith("path:") and len(version) <= 64:
        return ""
    return "a mise version is letters, digits and + . _ : -, and not a path"


def mise_key(name):
    """`name` as a TOML key: bare when it can be, else double-quoted."""
    return name if BARE_KEY.match(name) else '"%s"' % name


def _unquote(token):
    return token[1:-1] if token[:1] in "\"'" else token


def mise_text_problem(text, label="mise.toml"):
    """(problem, pins) of a mise config's text. `problem` is why `declare`
    will not write beside it, or "": every line but a comment or a blank must
    be min_version at the top, a [tools] or [tools.<name>] header, or a tool
    pinned to a string, an array of strings or an inline table of
    TOOL_OPTIONS; under [tools.<name>], a TOOL_OPTIONS key. Dotted keys,
    multi-line values, a tool defined twice, and a name `mise_name_problem`
    refuses are out too. When tomllib is here the text must also parse.
    `pins` maps each tool to its version string, or None."""
    hand = "; only [tools] versions are declared, so edit it by hand"
    pins = {}
    heads = set()
    # None at the top, TOOLS under [tools], else the tool [tools.<name>] sets.
    head = None
    TOOLS = ("[tools]",)
    for n, raw in enumerate(text.splitlines(), 1):
        line = _strip_comment(raw).strip()
        if not line:
            continue
        shown = _printable(line)[:40]
        if line.startswith("["):
            m = MISE_HEAD.match(line)
            first = _unquote(m.group(1)) if m else ""
            if not m or first != "tools":
                return ("%s has a %s table%s" % (label, shown, hand)), pins
            if m.group(2) is None:
                head = TOOLS
            else:
                head = _unquote(m.group(2))
                if mise_name_problem(head):
                    return ("%s has a %s table%s" % (label, shown, hand)), pins
                if head in pins:
                    return ("%s defines tool %s twice%s" % (label, shown, hand)), pins
                pins[head] = None
            if head in heads:
                return ("%s has %s twice%s" % (label, shown, hand)), pins
            heads.add(head)
            continue
        m = MISE_PAIR.match(line)
        if not m:
            return ("%s line %d is not a [tools] version: %s%s"
                    % (label, n, shown, hand)), pins
        key, value = _unquote(m.group(1)), m.group(2).strip()
        if head is None:
            if key in MISE_TOP and MISE_STR.match(value):
                continue
            return ("%s sets %s at the top%s" % (label, _printable(key)[:40], hand)), pins
        if head is not TOOLS:
            if key not in TOOL_OPTIONS or m.group(1) != key:
                return ("%s gives tool %s a %s option%s"
                        % (label, head, _printable(key)[:40], hand)), pins
            if not (MISE_STR.match(value) or (key == "os" and MISE_ARR.match(value))):
                return ("%s line %d is not a [tools] version: %s%s"
                        % (label, n, shown, hand)), pins
            if key == "version":
                pins[head] = _unquote(value)
            continue
        if mise_name_problem(key):
            return ("%s line %d is not a [tools] version: %s%s"
                    % (label, n, shown, hand)), pins
        if key in pins:
            return ("%s defines tool %s twice%s" % (label, key, hand)), pins
        if MISE_STR.match(value):
            pins[key] = _unquote(value)
        elif MISE_ARR.match(value):
            pins[key] = None
        elif MISE_INLINE.match(value):
            got = dict()
            for opt, val in MISE_INLINE_PAIR.findall(value):
                if opt not in TOOL_OPTIONS or opt in got or (
                        opt == "version" and not MISE_STR.match(val)):
                    return ("%s gives tool %s a %s option%s"
                            % (label, key, _printable(opt)[:40], hand)), pins
                got[opt] = val
            pins[key] = _unquote(got["version"]) if "version" in got else None
        else:
            return ("%s line %d is not a [tools] version: %s%s"
                    % (label, n, shown, hand)), pins
    try:
        import tomllib
    except ImportError:
        tomllib = None
    if tomllib is not None:
        try:
            tomllib.loads(text)
        except tomllib.TOMLDecodeError as e:
            return ("%s does not parse as TOML (%s)%s"
                    % (label, _printable(str(e))[:60], hand)), pins
    return "", pins


TOOL_VERSIONS = ".tool-versions"
VERSION_WORD = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+._:@/<>=~^-]*\Z")


def tool_versions_problem(text, label=TOOL_VERSIONS):
    """Why the asdf-style `.tool-versions` `text` is not safe for mise to
    read, or "". mise renders it as a tera template too, without asking for
    trust, so each line but a comment or a blank must be a tool
    `mise_name_problem` passes and versions of VERSION_WORD."""
    for n, raw in enumerate(text.splitlines(), 1):
        words = raw.split("#", 1)[0].split()
        if not words:
            continue
        if mise_name_problem(words[0]) or len(words) < 2 or not all(
                VERSION_WORD.match(w) for w in words[1:]):
            return ("%s line %d is not a tool and its versions: %s; edit it by hand"
                    % (label, n, _printable(raw.strip())[:40]))
    return ""


def mise_problem(path, label="mise.toml"):
    """Why `declare` will not write beside the mise config at `path`
    (`mise_text_problem`, or `tool_versions_problem` for a .tool-versions),
    or "". A missing file has none."""
    if not os.path.lexists(path):
        return ""
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            text = fh.read()
    except UnicodeDecodeError:
        return "%s is not UTF-8, so edit it by hand" % label
    except OSError as e:
        return "%s cannot be read (%s), so edit it by hand" % (label, e.strerror or "error")
    if os.path.basename(path) == TOOL_VERSIONS:
        return tool_versions_problem(text, label)
    return mise_text_problem(text, label)[0]


MISE_FILE = re.compile(r"^\.?mise(\.[^/]+)?\.toml\Z")


def _mise_files_in(d):
    """Every file in directory `d` that mise reads as config, sorted:
    mise.toml, .mise.toml, mise.<env>.toml, mise.local.toml and their dot
    forms, .tool-versions, .config/mise*.toml, and every .toml under mise/,
    .mise/ and .config/mise/ (config.toml, conf.d/)."""
    found = []

    def listed(where):
        try:
            return sorted(os.listdir(where))
        except OSError:
            return []
    for name in listed(d):
        if MISE_FILE.match(name) or name == TOOL_VERSIONS:
            found.append(os.path.join(d, name))
    for name in listed(os.path.join(d, ".config")):
        if MISE_FILE.match(name) and not name.startswith("."):
            found.append(os.path.join(d, ".config", name))
    for sub in ("mise", ".mise", os.path.join(".config", "mise")):
        top = os.path.join(d, sub)
        if not os.path.isdir(top):
            continue
        for where, dirs, files in os.walk(top):
            dirs.sort()
            for name in sorted(files):
                if name.endswith(".toml"):
                    found.append(os.path.join(where, name))
    return found


def mise_configs(target, base):
    """The mise config files mise reads when run in `target`: those of
    `target` and of each directory above it up to and including `base`, or of
    `target` alone when it is not inside `base`. `mise_env` trusts exactly
    these, and the board runs mise only after `mise_chain_problem` passes
    them."""
    target = os.path.realpath(target)
    base = os.path.realpath(base)
    dirs = [target]
    if target.startswith(base + os.sep):
        d = target
        while d != base:
            d = os.path.dirname(d)
            dirs.append(d)
    out = []
    for d in dirs:
        for path in _mise_files_in(d):
            if path not in out:
                out.append(path)
    return out


# Settings that would make mise read project files other than the ones
# `_mise_files_in` names.
MISE_FILENAME_VARS = ("MISE_DEFAULT_CONFIG_FILENAME", "MISE_DEFAULT_TOOL_VERSIONS_FILENAME",
                      "MISE_OVERRIDE_CONFIG_FILENAMES",
                      "MISE_OVERRIDE_TOOL_VERSIONS_FILENAMES")


def mise_env(target, base, env=None):
    """`env` (default os.environ) for a mise run in `target` that reads only
    `mise_configs(target, base)`: those files trusted and no other, the
    search for project configs stopped above the chain's top directory
    (MISE_CEILING_PATHS), no file-name override, and MISE_YES=0, since
    `yes` would answer mise's trust prompt for a config nobody checked.
    The owner's global config is still read; it is theirs."""
    out = dict(os.environ if env is None else env)
    for var in MISE_FILENAME_VARS:
        out.pop(var, None)
    target = os.path.realpath(target)
    base = os.path.realpath(base)
    top = base if target.startswith(base + os.sep) or target == base else target
    out.update({"MISE_YES": "0",
                "MISE_CEILING_PATHS": os.path.dirname(top),
                "MISE_TRUSTED_CONFIG_PATHS": os.pathsep.join(mise_configs(target, base))})
    return out


def mise_chain_problem(target, base):
    """Why a mise run in `target` is not safe to start, or "": the first
    `mise_configs` file `mise_problem` refuses, named relative to `base`."""
    base = os.path.realpath(base)
    for path in mise_configs(target, base):
        label = os.path.relpath(path, base)
        problem = mise_problem(path, label)
        if problem:
            return problem
    return ""


def _newline(text):
    """The line ending `text` already uses: CRLF only when most of its line
    breaks are CRLF, else LF."""
    crlf = text.count("\r\n")
    return "\r\n" if crlf > text.count("\n") - crlf else "\n"


def _write_text(path, text):
    """Write `text` to `path` through a temp file, making its directory. The
    text's own line endings are written unchanged."""
    where = os.path.dirname(path)
    if where:
        os.makedirs(where, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(tmp, path)


def _entry_name(entry):
    """(kind, name) of a `brew "x"` or `cask "x"` entry, else None."""
    m = re.match(r'^(brew|cask)\s+"([^"]+)"', entry)
    return (m.group(1), m.group(2)) if m else None


def _declared(base):
    """[(kind, name)] of every brew and cask in `union(base)` and in
    `upkeep/Brewfile`, which upkeep installs on every machine."""
    out = []
    for entry in list(union(base)[0]) + sorted(machine_entries(base)):
        got = _entry_name(entry)
        if got:
            out.append(got)
    return out


def _sub_name(head):
    """The tool part of a normalized `tools.<name>` header, unquoted."""
    rest = head[len("tools."):]
    if len(rest) >= 2 and rest[0] == rest[-1] and rest[0] in "\"'":
        rest = rest[1:-1]
    return rest


def _mise_set(path, name, version, why):
    """`path`'s text with `name` under its tools table, replacing its entry,
    or the version line inside a `[tools.<name>]` subtable when one exists.
    Returns (changed, entry, note, text); every other line, comment and line
    ending stays. Writes nothing: `declare` checks `text` first."""
    line = '%s = "%s"' % (mise_key(name), version)
    if why:
        line += "  # " + why
    version_line = 'version = "%s"' % version
    if why:
        version_line += "  # " + why
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            text = fh.read()
    except OSError:
        text = ""
    eol = _newline(text)
    lines = text.splitlines()
    heads = []
    for i, raw in enumerate(lines):
        bare = _strip_comment(raw).strip()
        if bare.startswith("[") and bare.endswith("]"):
            heads.append((i, re.sub(r"\s+", "", bare[1:-1])))
    tools_at = sub_at = None
    for i, head in heads:
        if head == "tools":
            tools_at = i
        elif head.startswith("tools.") and _sub_name(head) == name:
            sub_at = i
            break

    def section_end(at):
        later = [i for i, _head in heads if i > at]
        return later[0] if later else len(lines)

    if sub_at is not None:
        end = section_end(sub_at)
        replaced = None
        insert_at = sub_at + 1
        for i in range(sub_at + 1, end):
            bare = _strip_comment(lines[i]).strip()
            if "=" in bare:
                key = bare.split("=", 1)[0].strip().strip("\"'")
                if key == "version":
                    replaced = i
                    break
                insert_at = i + 1
        if replaced is not None:
            if lines[replaced] == version_line:
                return False, version_line, "already pinned to %s" % version, text
            lines[replaced] = version_line
        else:
            lines.insert(insert_at, version_line)
        return True, version_line, "", eol.join(lines) + eol
    start = tools_at
    insert_at = replaced = None
    if start is not None:
        end = section_end(start)
        insert_at = start + 1
        for i in range(start + 1, end):
            bare = _strip_comment(lines[i]).strip()
            if "=" in bare:
                key = bare.split("=", 1)[0].strip().strip("\"'")
                if key == name:
                    replaced = i
                    break
                insert_at = i + 1
    if replaced is not None:
        if lines[replaced] == line:
            return False, line, "already pinned to %s" % version, text
        lines[replaced] = line
    elif start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("# Pinned toolchains, installed by `mise install --locked`.")
        lines.append("[tools]")
        lines.append(line)
    else:
        lines.insert(insert_at, line)
    return True, line, "", eol.join(lines) + eol


def declare(base, kind, name, version=None, subject=None, why=None, force=False):
    """Declare one machine tool in the repository's own files.

    `kind` is brew, cask or mise. With no `subject`, a brew or cask line goes
    in `base/Brewfile` and a mise pin in `base/mise.toml`; a subject's goes in
    that subject's root. A brew or cask already declared anywhere in
    `union(base)` or `upkeep/Brewfile` is refused with `changed` False, and so
    is a name declared with the other kind, unless `force`. A mise pin replaces
    its entry rather than adding a second. Returns {path, kind, name, changed,
    target, entry, note, why}: `path` is relative to `base`, `target` the
    file's directory, `why` the comment as written. Never writes Brewfile.all.

    Refused before anything is written: a brew or cask name `name_problem`
    refuses, a mise name or version that is not plain (`mise_name_problem`,
    `mise_version_problem`), any mise config `mise_chain_problem` refuses in
    the target directory or above it up to `base`, and a mise.toml whose new
    text `mise_text_problem` refuses or that would not pin `name` to
    `version`. `why` is `clean_why`'d, so it is one comment line.
    """
    base = os.path.realpath(os.path.expanduser(base))
    kind = str(kind or "").strip()
    name = str(name or "").strip()
    why = clean_why(why)
    got = {"path": "", "kind": kind, "name": name, "changed": False,
           "target": base, "entry": "", "note": "", "subject": "", "why": why}
    if kind not in ("brew", "cask", "mise"):
        got["note"] = "kind must be brew, cask or mise"
        return got
    if not name:
        got["note"] = "a tool needs a name"
        return got
    if kind in ("brew", "cask"):
        problem = name_problem(kind, name, allowed_taps(base))
    else:
        problem = mise_name_problem(name) or (
            mise_version_problem(str(version)) if version else "")
    if problem:
        got["note"] = problem
        return got
    target_root = base
    if subject:
        from . import subjects
        found = subjects.find(subject, base)
        if not found:
            got["note"] = "no subject %r" % subject
            return got
        target_root = found["root"]
        got["subject"] = found["id"]
    if kind in ("brew", "cask"):
        for have_kind, have_name in _declared(base):
            if have_name != name:
                continue
            if have_kind == kind:
                if not force:
                    got["note"] = "already declared as a %s in the Brewfiles" % kind
                    return got
            elif not force:
                got["note"] = ("already declared as a %s; a name has one kind"
                               % have_kind)
                return got
        path = os.path.join(target_root, "Brewfile")
        try:
            with open(path, encoding="utf-8", newline="") as fh:
                text = fh.read()
        except OSError:
            text = ""
        eol = _newline(text)
        if text and not text.endswith("\n"):
            text += eol
        entry = '%s "%s"' % (kind, name)
        if why:
            entry += "  # " + why
        _write_text(path, text + entry + eol)
        got.update({"path": os.path.relpath(path, base), "changed": True,
                    "target": os.path.dirname(path), "entry": entry})
        return got
    version = str(version or "latest")
    path = root_mise(target_root)[0]
    problem = mise_chain_problem(target_root, base)
    if problem:
        got["note"] = problem
        return got
    changed, entry, note, text = _mise_set(path, name, version, why)
    if changed:
        problem, pins = mise_text_problem(text)
        if problem or pins.get(name) != version:
            got["note"] = problem or (
                "mise.toml pins %s in a form declare cannot rewrite, so edit it "
                "by hand" % name)
            return got
        _write_text(path, text)
    got.update({"path": os.path.relpath(path, base), "changed": changed,
                "target": os.path.dirname(path), "entry": entry, "note": note})
    return got


def note_declared(base, record, where=None):
    """Append or replace `record` in tools.json's `declared` list, by kind
    and name. Best effort: never raises, and returns False when unwritten."""
    try:
        rec = dict(record or {})
        for key in ("name", "kind", "path", "subject", "why"):
            rec.setdefault(key, "")
        rec.setdefault("at", now_stamp())

        def change(doc):
            got = doc.get("declared")
            if not isinstance(got, list):
                got = []
            key = (rec.get("kind"), rec.get("name"))
            for i, old in enumerate(got):
                if isinstance(old, dict) and (old.get("kind"), old.get("name")) == key:
                    got[i] = rec
                    break
            else:
                got.append(rec)
            doc["declared"] = got
        return update(change, where)
    except Exception:                                        # noqa: BLE001
        return False


# --------------------------------------------------------------------- CLI

def _cli(argv):
    """python3 -m tutorboard.toolplan <command> --atlas <root> ...

        union [--write]   the Brewfile union; --write writes Brewfile.all
                          when it changed and says `rewritten` or `unchanged`.
                          Each refused line goes to stderr
        plan              one line per descriptor: name, path, subjects and
                          the epoch of its last update, tab-separated; each
                          conflict to stderr, and exit 3 when there is one
        record            tools.sh's TSV rows on stdin into tools.json
        markers           one line per marker: subject, marker, lock, dir
        pinned <dir>      the tools <dir>'s own mise.toml pins, one a line
        root-mise-tools   Atlas's own mise.toml pins, one name a line
    """
    args = list(argv)
    base = None
    if "--atlas" in args:
        i = args.index("--atlas")
        base = os.path.realpath(args[i + 1])
        del args[i:i + 2]
    if base is None:
        from . import subjects
        base = subjects.root()
    cmd = args[0] if args else ""
    if cmd == "union":
        got, labels, refused = checked(base)
        for label, line, why in refused:
            sys.stderr.write("refused %s: %s (%s)\n" % (_printable(label), ascii(line), why))
        if "--write" in args:
            changed, path = write_union(base)
            print("%s (%d entries from %s%s)" % (
                "rewritten" if changed else "unchanged", len(got),
                _printable(", ".join(labels)),
                "; %d line(s) refused, see tools.json refused_brew" % len(refused)
                if refused else ""))
            return 0
        sys.stdout.write(union_text(base))
        return 0
    if cmd == "plan":
        plan, conflicts = descriptors(base)
        tools = read().get("tools") or {}
        for p in plan:
            last = (tools.get(p["name"]) or {}).get("attempted") or \
                (tools.get(p["name"]) or {}).get("updated")
            epoch = 0
            if last:
                try:
                    epoch = int(datetime.strptime(last[:19], "%Y-%m-%dT%H:%M:%S")
                                .timestamp())
                except ValueError:
                    epoch = 0
            print("%s\t%s\t%s\t%d" % (p["name"], p["path"], ",".join(p["subjects"]),
                                      epoch))
        for c in conflicts:
            sys.stderr.write("%s: declared differently in %s; the copies must be the "
                             "same bytes\n" % (c["name"], " and ".join(
                                 os.path.relpath(p, base) for p in c["paths"])))
        return 3 if conflicts else 0
    if cmd == "record":
        keys = ("name", "event", "step", "version", "found", "bin", "dir",
                "every_days", "stale_days", "why")
        rows = []
        for line in sys.stdin.read().splitlines():
            if line.strip():
                rows.append(dict(zip(keys, line.split("\t"))))
        record(base, rows)
        return 0
    if cmd == "pinned" and len(args) > 1:
        for name in pinned_in(args[1]):
            print(name)
        return 0
    if cmd == "root-mise-tools":
        for name, _version in root_mise_tools(base):
            print(name)
        return 0
    if cmd == "markers":
        for ident, root in subjects_of(base):
            for marker, lock, d in markers(root):
                print("%s\t%s\t%s\t%s" % (ident, marker, lock, d))
        return 0
    sys.stderr.write(_cli.__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
