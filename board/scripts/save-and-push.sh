#!/usr/bin/env bash
# save-and-push.sh -- commit the named paths of this repository, then push.
#
#   board/scripts/save-and-push.sh "message" -- <path>...
#
# A thin CLI over `tutorboard/gitops.py` (`save`). The working directory picks
# the repository; paths are relative to its root. A commit carries named paths
# only, no trailers; the push merges origin first and is never forced.
# Exit 0 on success or when there was nothing to commit.
set -uo pipefail
BOARD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd -P)"
PYTHONPATH="$BOARD${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m tutorboard.gitops "$@"
