#!/usr/bin/env bash
# ===========================================================================
#  serve.sh -- start the allocation the board lives in, and keep it starting.
#
#      bash board/scripts/serve.sh            start the chain
#      bash board/scripts/serve.sh status     which generation is up, and where
#      bash board/scripts/serve.sh stop       end it
#      bash board/scripts/serve.sh restart    end it and start a fresh one
#
#  THIS IS THE ONE COMMAND TO RUN AFTER `scancel -u $USER`. Cancelling every job
#  you hold is the thing that really ends the chain -- it takes the running
#  generation and the successor queued behind it in the same breath, which
#  cancelling one job at a time cannot do -- so this is how it comes back, and it
#  is the whole of what has to be remembered. A login also repairs a chain that
#  was cancelled rather than stopped, but nobody should have to rely on noticing.
#
#  It needs no `tutor` on the PATH and does not care which directory it is run
#  from: the checkout comes from this file's own location, the same rule ship.sh
#  follows and for the same reason. `tutor serve` is the same command, shorter,
#  once install.sh has run.
# ===========================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd -P)"
# `-f` and not `-x`: this repository is cloned with core.fileMode off, so the
# execute bit on a tracked file is not something to test for. Nothing here execs
# the tool anyway -- python3 is given the path.
[ -f "$HERE/bin/tutor" ] || {
  echo "cannot find bin/tutor next to $0 -- this script has been moved out of the"
  echo "tool's scripts/ directory, which is the only place it knows itself from." >&2
  exit 1
}

exec python3 "$HERE/bin/tutor" serve "$@"
