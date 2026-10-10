#!/usr/bin/env python3
"""Move a subject's export approvals off its thread file into tutorboard.json.

    python3 board/scripts/migrate-exports.py <subject dir> [--dry-run]

Every path a thread of `<subject>/threads.json` marks `"aggregate": true`
becomes one `relay.exports` entry in `<subject>/tutorboard.json`, its glob the
path itself with any glob character escaped, so it matches that path and
nothing else. A csv or json entry carries `"aggregate": true`, which is what
approves one (`tutorboard/exports.py`). A path listed but never marked
aggregate is not approved before or after, and gets no entry. Entries already
in `relay.exports` are kept, and the new ones follow them.

It prints the old list (the marked paths) and the new one (the entries), and
writes the file unless `--dry-run`. The owner commits the result: a turn may
not commit a change to `relay.exports`.

Stdlib only.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from tutorboard import exports                                     # noqa: E402


def escape(path):
    """`path` as a glob that matches exactly it."""
    out = []
    for ch in path:
        out.append("[%s]" % ch if ch in "*?[" else ch)
    return "".join(out)


def old_marks(threads_doc):
    """Every path the thread file let be published, in file order, once
    each (`old_approves`)."""
    out = []
    for t in (threads_doc or {}).get("threads") or []:
        for e in t.get("exports") or []:
            rel = exports.rel(e.get("path")) if isinstance(e, dict) else None
            if rel and rel not in out and old_approves(threads_doc, rel):
                out.append(rel)
    return out


def old_approves(threads_doc, path):
    """The thread file's rule: some thread marks exactly `path` aggregate,
    and it passes the extension and `results/` checks every export did."""
    path = exports.rel(path)
    if not path or not path.startswith("results/"):
        return False
    if os.path.splitext(path)[1].lower() not in exports.EXPORT_EXTS:
        return False
    return any(exports.exportable(
        {"exports": [e for e in t.get("exports") or [] if isinstance(e, dict)]},
        path) for t in (threads_doc or {}).get("threads") or [])


def entries_for(marks):
    """The `relay.exports` entries that approve exactly `marks`."""
    out = []
    for rel in marks:
        one = {"glob": escape(rel)}
        if os.path.splitext(rel)[1].lower() in exports.ROW_EXTS:
            one["aggregate"] = True
        out.append(one)
    return out


def migrate(subject, dry_run=False, say=print):
    """Write the entries into `<subject>/tutorboard.json`. `(marks, entries)`,
    where `entries` is the whole new `relay.exports`."""
    with open(os.path.join(subject, "threads.json"), "r",
              encoding="utf-8") as fh:
        doc = json.load(fh)
    target = os.path.join(subject, exports.CONFIG)
    try:
        with open(target, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    except OSError:
        cfg = {}
    relay = cfg.get("relay") if isinstance(cfg.get("relay"), dict) else {}
    had, problems = exports.entries(relay.get("exports"))
    if problems:
        raise SystemExit("%s: relay.exports is not valid: %s"
                         % (target, "; ".join(problems)))
    marks = old_marks(doc)
    new = list(had) + [e for e in entries_for(marks) if e not in had]
    say("old: %d path(s) marked aggregate in threads.json" % len(marks))
    for p in marks:
        say("  " + p)
    say("new: %d relay.exports entr%s in tutorboard.json"
        % (len(new), "y" if len(new) == 1 else "ies"))
    for e in new:
        say("  " + json.dumps(e, sort_keys=True))
    if not dry_run:
        relay["exports"] = new
        cfg["relay"] = relay
        tmp = target + ".new"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, target)
        say("wrote %s" % target)
    return marks, new


def main(argv):
    args = [a for a in argv if a != "--dry-run"]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    migrate(os.path.abspath(args[0]), dry_run="--dry-run" in argv)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
