#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# cutover.sh -- put the overhaul live on this Mac, or take it back.
#
#   bash board/scripts/cutover.sh --plan                  what --run would do
#   bash board/scripts/cutover.sh --rehearse <scratch>    steps 1-10 on a copy,
#                                                         then a rollback, compared
#   bash board/scripts/cutover.sh --run                   steps 1-12, for real
#   bash board/scripts/cutover.sh --rollback <manifest>   undo a run not yet pushed
#
# --run is the owner's, from Terminal, with the cwd the top of a clean worktree
# of this Atlas checked out at `overhaul`. It refuses anywhere else. It prints
# each step and ends on one line: CUTOVER OK <sha>, or CUTOVER ROLLED BACK:
# <reason>, with the old system answering again.
#
# Options: --atlas <dir> (default: the main checkout of this repository),
# --ref <rev> (default overhaul), --keep (rehearse: keep the scratch dir).
#
# The steps and the manifest are cutover.py's: every move, every label booted
# out, the tailscale capture and main's sha before the merge go to
# ~/Archive/atlas-migration/<date>/cutover-manifest.json before they happen,
# and --run rolls itself back when any check or the push fails.
#
# Run it from a checkout of the overhaul (a worktree is fine): before the
# merge, the main checkout does not hold this script.
# ---------------------------------------------------------------------------
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

case "${1:-}" in
  --plan|--run|--rehearse|--rollback) : ;;
  -h|--help) sed -n '3,27p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) echo "usage: cutover.sh --plan | --rehearse <scratch> | --run | --rollback <manifest>" >&2
     exit 2 ;;
esac

if [ "$(uname -s)" != "Darwin" ]; then
  echo "cutover.sh: the cutover is the Mac's; this is $(uname -s)" >&2
  exit 2
fi

PY="$(command -v python3)" || { echo "cutover.sh: no python3 on PATH" >&2; exit 2; }
exec "$PY" "$HERE/cutover.py" "$@"
