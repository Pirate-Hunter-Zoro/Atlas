#!/usr/bin/env bash
# ===========================================================================
#  ship.sh -- commit and push this tool, then put the board server on it.
#
#  The board server reads `serve.py` and `tutorboard/` once, when it starts.
#  It notices committed board code by itself and exits for launchd to restart
#  it once no turn runs; this restarts it now instead, so a ship lands at once.
#
#      bash scripts/ship.sh ["commit message"]
#
#  It commits ONLY the tool's own directory. Everything lives in one repository,
#  and a ship that ran `git add -A` would file every subject's unfinished work
#  under a commit message about the board.
#
#  The commit is authored by whoever `git config user.name` says. No trailers,
#  no co-authors, no attribution to any assistant -- the work belongs to the
#  person whose repository this is and the history should say only that.
# ===========================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$HERE" || { echo "cannot enter $HERE" >&2; exit 1; }

MSG="${1:-board and tutor updates}"

# The tool's path inside its repository (`board`), asked of git rather than
# typed, so a rename never turns shipping into "commit everything". Empty means
# the tool is the repository root, and then the pathspec is the whole tree.
REL="$(git -C "$HERE" rev-parse --show-prefix 2>/dev/null)"
REL="${REL%/}"

echo "== the tool (${REL:-the repository}) =="
bash "$HERE/scripts/save-and-push.sh" "$MSG" -- "${REL:-.}"
status=$?
if [ $status -ne 0 ]; then
  echo
  echo "push did not succeed, so nothing has been restarted." >&2
  echo "The server is still on the old code, which is the safe place for it" >&2
  echo "to be while the change is not saved anywhere." >&2
  exit $status
fi

# The one LaunchAgent. `kickstart -k` kills the running server and starts it
# again at once; a turn in flight is cut, and its message stays owed and is
# answered after the restart. TUTORBOARD_LABEL names another job, as it does
# for install.sh.
echo
TARGET="gui/$(id -u)/${TUTORBOARD_LABEL:-tutor-board}"
if command -v launchctl >/dev/null 2>&1 && launchctl print "$TARGET" >/dev/null 2>&1; then
  launchctl kickstart -k "$TARGET" && echo "restarted $TARGET"
else
  echo "no LaunchAgent tutor-board here; run board/install.sh to install it" >&2
fi

echo
echo "shipped."
