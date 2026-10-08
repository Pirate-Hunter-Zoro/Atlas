#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# rebuild-packet.sh -- the four packet documents, as .docx AND as .pdf.
#
#   bash research/TRD-EHR/scripts/rebuild-packet.sh [--strict] [--all]
#
# `board build` makes both: the .docx is what a journal takes and what the
# senior author marks up, and the .pdf is the reading copy the board shows.
#
# THE FOUR, NAMED. Not every .md in the repository: that is
# fifty-five documents, most of them sections and review notes, and a PDF of
# each would flood the board's document drawer past the two dozen it offers and
# bury the packet inside it. These four are the packet, they are what STEP 5 of
# `planning/TRD-EHR_TODO.txt` rebuilds, and they are the four worth reading
# whole.
#
# Only what changed is rebuilt, in both formats -- an output younger than its
# .md is already the document. `--all` rebuilds all four regardless.
#
#   --strict   fail on a figure that will not sit on the page, which is the run
#              to make before submitting
#
# Exits 0 when every document that needed building was built, with its figures.
# ---------------------------------------------------------------------------
set -uo pipefail

# The paper folder and the repository, from THIS FILE rather than from the
# working directory, so the script gives one answer wherever it is run from.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKSPACE="$(dirname "$HERE")"
PAPER="$WORKSPACE/paper1-trd-prediction"
ROOT="$(git -C "$WORKSPACE" rev-parse --show-toplevel 2>/dev/null || dirname "$(dirname "$WORKSPACE")")"

# One builder for all of Atlas: `board build`, which carries Paper-Writer's
# converter (reference .docx from formats/, resource path, lost-figure check).
BOARD="$ROOT/board/bin/board"
if [ ! -f "$BOARD" ]; then
  echo "cannot find the board CLI at $BOARD" >&2
  exit 1
fi

STRICT=()
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --strict|-s) STRICT=(--strict) ;;
    --all|-a)    FORCE=1 ;;
    *) echo "unknown option: $arg (--strict, --all)" >&2; exit 2 ;;
  esac
done

PACKET=(manuscript.md supplement.md cover_letter.md tripod_ai_checklist.md)
for name in "${PACKET[@]}"; do
  [ -f "$PAPER/$name" ] || { echo "no such document: $PAPER/$name" >&2; exit 1; }
done

status=0
for fmt in docx pdf; do
  echo "== .$fmt =="
  for name in "${PACKET[@]}"; do
    src="$PAPER/$name"
    out="${src%.md}.$fmt"
    if [ "$FORCE" = 1 ] || [ ! -e "$out" ] || [ "$src" -nt "$out" ]; then
      python3 "$BOARD" build "$src" --format "$fmt" ${STRICT[@]+"${STRICT[@]}"} || status=1
    else
      echo "$name: .$fmt already current"
    fi
  done
  echo
done

exit $status
