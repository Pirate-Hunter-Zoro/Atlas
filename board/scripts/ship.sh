#!/usr/bin/env bash
# ===========================================================================
#  ship.sh -- commit and push this tool, then put every course on the new code.
#
#  A board and a tutor are long-lived processes that read `serve.py` and
#  `bin/tutor` once, when they start. Changing this repository therefore does
#  nothing to a course that is already running: the pages are served from disk
#  and look new while the endpoints and the daemon behind them are the old ones.
#  That is invisible from the outside and it has cost an evening more than once.
#
#  So shipping is one act, not two: commit, push, and bounce what is running.
#
#      bash scripts/ship.sh ["commit message"]
#
#  It commits ONLY the tool's own directory. Everything lives in one repository
#  now, and a ship that ran `git add -A` would file nine workspaces' unfinished
#  work under a commit message about the board.
#
#  The commit is authored by whoever `git config user.name` says. No trailers,
#  no co-authors, no attribution to any assistant -- the work belongs to the
#  person whose repository this is and the history should say only that.
# ===========================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/tool.sh
. "$HERE/scripts/tool.sh"
cd "$HERE" || { echo "cannot enter $HERE" >&2; exit 1; }

MSG="${1:-board and tutor updates}"

# The TOOL's path inside the repository, worked out rather than typed: this is
# `board` today and the point of deriving it is that a rename does not silently
# turn shipping into "commit everything". `scripts/tool.sh` is the one place it
# is derived, because `save-and-push.sh` needs the same answer and the copy it
# had was wrong.
REL="$(tool_prefix)"

echo "== the tool (${REL:-the repository}) =="
# ONLY the tool's own paths. There is one repository now: without the pathspec,
# shipping a change to the board would sweep up whatever is uncommitted in nine
# other workspaces and commit it under "board and tutor updates". A course's
# half-finished proof is not a board update and must never be filed as one.
if [ -n "$REL" ]; then
  bash "$HERE/scripts/save-and-push.sh" "$MSG" -- "$REL"
else
  bash "$HERE/scripts/save-and-push.sh" "$MSG"
fi
status=$?
if [ $status -ne 0 ]; then
  echo
  echo "push did not succeed, so nothing has been restarted." >&2
  echo "Running processes are still on the old code, which is the safe place" >&2
  echo "for them to be while the change is not saved anywhere." >&2
  exit $status
fi

# save-and-push.sh already bounces the boards when it is this repository being
# pushed. The tutors are the other half, and they are only bounced from here --
# a course pushing its own homework has no business restarting anybody's tutor.
echo
if command -v tutor >/dev/null 2>&1; then
  tutor restart --tutors
else
  echo "tutor is not on PATH; run 'tutor restart --tutors' by hand" >&2
fi

echo
echo "shipped."
