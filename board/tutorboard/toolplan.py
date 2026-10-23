"""The machine's tools, as the tree declares them, and what became of them.

Three layers, each read from the subjects and never from a list. The board
server runs none of them: `scripts/setup.sh` installs, `scripts/tools.sh`
reads descriptors, and `scripts/brew-upgrade.py` keeps all three current.

  BREWFILES    the root `Brewfile` plus each subject's own, as one sorted and
               deduplicated union (`union_text`). setup.sh bundles it with
               --no-upgrade and brew-upgrade.py checks it, from
               `~/.local/state/atlas-setup/Brewfile.all`, rewritten only when
               it changes (`write_union`). An entry that leaves the union is
               remembered in tools.json `left_brew`; nothing is uninstalled.
  MISE         a subject's `mise.toml` and `mise.lock` pin its toolchains.
               `marker_dirs` finds a marker at a subject's root and one
               directory down, skipping SKIP.
  DESCRIPTORS  `<subject>/tools/<name>.sh`, read by scripts/tools.sh. One name
               in two subjects must be the same bytes (`descriptors`).

State is tools.json in the board's state directory: one record per tool
tools.sh has handled, `left` for one no longer declared, `left_brew`, and
`pins`, the mise pins brew-upgrade.py found behind, which brief.py puts in
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

# A marker's lockfile, which must sit beside it.
MARKERS = (("mise.toml", "mise.lock"), ("Cargo.toml", "Cargo.lock"),
           ("pubspec.yaml", "pubspec.lock"))
# Never looked into for a marker: build output and environments.
SKIP = ("target", "build", ".dart_tool", ".venv", "node_modules")
# A Brewfile's entries, in the order brew bundle needs them: a tap first.
KINDS = ("tap", "brew", "cask", "mas", "whalebrew", "vscode")


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


def entries(path):
    """The entries of one Brewfile, comments and blank lines dropped and
    whitespace collapsed; [] when it cannot be read."""
    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    out = []
    for line in raw:
        line = " ".join(_strip_comment(line).split())
        if line:
            out.append(line)
    return out


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


def union(base):
    """(sorted unique entries, [labels]) over every Brewfile."""
    seen = set()
    labels = []
    for label, path in brewfiles(base):
        labels.append(label)
        seen.update(entries(path))
    return sorted(seen, key=lambda e: (_kind(e), e)), labels


def union_text(base):
    got, labels = union(base)
    head = ("# Written by scripts/setup.sh and scripts/brew-upgrade.py; edit the "
            "Brewfiles it joins:\n# %s\n" % ", ".join(labels or ["(none)"]))
    return head + "".join(e + "\n" for e in got)


def write_union(base, dest=None):
    """Write the union to `dest` (Brewfile.all) when it differs. (changed,
    path). An entry that left it goes into tools.json `left_brew`, and one
    that came back comes out."""
    dest = dest or union_path()
    text = union_text(base)
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
    gone, back = before - now, now

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


# --------------------------------------------------------------------- CLI

def _cli(argv):
    """python3 -m tutorboard.toolplan <command> --atlas <root> ...

        union [--write]   the Brewfile union; --write writes Brewfile.all
                          when it changed and says `rewritten` or `unchanged`
        plan              one line per descriptor: name, path, subjects and
                          the epoch of its last update, tab-separated; each
                          conflict to stderr, and exit 3 when there is one
        record            tools.sh's TSV rows on stdin into tools.json
        markers           one line per marker: subject, marker, lock, dir
        pinned <dir>      the tools <dir>'s own mise.toml pins, one a line
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
        if "--write" in args:
            changed, path = write_union(base)
            got, labels = union(base)
            print("%s (%d entries from %s)" % ("rewritten" if changed else "unchanged",
                                                len(got), ", ".join(labels)))
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
    if cmd == "markers":
        for ident, root in subjects_of(base):
            for marker, lock, d in markers(root):
                print("%s\t%s\t%s\t%s" % (ident, marker, lock, d))
        return 0
    sys.stderr.write(_cli.__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
