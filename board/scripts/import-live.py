#!/usr/bin/env python3
"""Turn one workspace's live/ into one open session, or undo that.

    import-live.py --atlas <root> --workspace <dir> --subject <post-merge id>
                   [--manifest <path>] [--dry-run]
    import-live.py --reverse <manifest>

The subject id is the post-merge one: `research/X` and `practice/X` become
`projects/X`. Every move is appended to the manifest (JSON lines, default
`<atlas>/sessions/.import-manifest.jsonl`); what the session does not keep is
set aside in `<manifest>.kept/`. `--reverse` undoes every import the manifest
records, newest first. `live/archive/` is left for the caller (D9).

The cutover (board/scripts/cutover.sh) runs it once per workspace. The
destination of each live/ entry is `tutorboard.sessions.import_live`'s.
"""

import argparse
import os
import sys

BOARD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BOARD)

from tutorboard import sessions                                  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(prog="import-live.py",
                                 description=__doc__.split("\n\n")[0])
    ap.add_argument("--atlas", help="the Atlas root that gets sessions/")
    ap.add_argument("--workspace", help="the directory holding live/")
    ap.add_argument("--subject", help="post-merge id: courses/X or projects/X")
    ap.add_argument("--manifest", help="where every move is appended")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan; change nothing")
    ap.add_argument("--reverse", metavar="MANIFEST",
                    help="undo every import this manifest records")
    args = ap.parse_args(argv)

    if args.reverse:
        undone, problems = sessions.reverse_import(args.reverse)
        print("reversed %d change(s) from %s" % (undone, args.reverse))
        for p in problems:
            print("  problem: %s" % p, file=sys.stderr)
        return 1 if problems else 0

    if not (args.atlas and args.workspace and args.subject):
        ap.error("--atlas, --workspace and --subject are required "
                 "(or --reverse <manifest>)")
    try:
        out = sessions.import_live(args.atlas, args.workspace, args.subject,
                                   manifest=args.manifest, dry_run=args.dry_run)
    except sessions.Refused as exc:
        print("import-live: %s" % exc, file=sys.stderr)
        return 1
    head = "dry run: " if args.dry_run else ""
    if out["session"]:
        print("%s%s -> session %s (%s)" % (head, out["workspace"],
                                           out["session"], out["subject"]))
    else:
        print("%s%s: no cards, no turns and no messages, so no session"
              % (head, out["workspace"]))
    if out["jobs"]:
        print("  job state: %d path(s) into %s/relay/state/"
              % (out["jobs"], out["subject"]))
    if out["imported"]:
        print("  into the session's imported/: %s" % ", ".join(out["imported"]))
    if out["kept"]:
        print("  set aside (dropped or not migrated): %s" % ", ".join(out["kept"]))
    if out["left"]:
        print("  left in live/: %s" % ", ".join(out["left"]))
    if args.dry_run:
        for rec in out["plan"]:
            print("  %-5s %s -> %s" % (rec["op"], rec["from"] or "", rec["to"] or ""))
    else:
        print("  manifest: %s" % out["manifest"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
