#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# rebuild-packet.sh -- the four packet documents, as .docx AND as .pdf.
#
#   bash research/TRD-EHR/scripts/rebuild-packet.sh [--strict]
#
# `rebuild` builds a .docx, which is what a journal takes and what the senior
# author marks up. The .pdf is the READING copy: the tutoring board renders PDFs
# and only PDFs, so the .pdf is how the manuscript is read on the iPad beside a
# lesson instead of on a laptop beside one. With no PDF the write-up was on no
# map, in no drawer, and unopenable on the glass -- `board/tutorboard/course/
# reading.py` finds any PDF in the workspace over 20 kB and needed nothing else.
#
# THE FOUR, NAMED. Not `rebuild --format pdf` over the repository: that is
# fifty-five documents, most of them sections and review notes, and a PDF of
# each would flood the board's document drawer past the two dozen it offers and
# bury the packet inside it. These four are the packet, they are what STEP 5 of
# `planning/TRD-EHR_TODO.txt` rebuilds, and they are the four worth reading
# whole.
#
# Only what changed is rebuilt, in both formats -- a .pdf younger than its .md
# is already the document. Run it after editing any of the four, which is the
# same moment you would have run `rebuild`.
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

# The converter is the harness's, not a bare pandoc line: a document rebuilt by
# hand has to be the document the pipeline would have produced, down to the
# resource path that lets a section's `../results/*.png` resolve. One repository
# now, so it is found in it -- `config/rebuild-alias.sh` still points a shell
# profile at `$HOME/Paper-Writer`, which is where the checkout used to be.
BUILD="$ROOT/projects/Paper-Writer/scripts/rebuild-docs.sh"
if [ ! -x "$BUILD" ]; then
  echo "cannot find Paper-Writer's builder at $BUILD" >&2
  echo "It is the converter the pipeline uses, and building these by hand with" >&2
  echo "a bare pandoc line produces a different document." >&2
  exit 1
fi

PACKET=(manuscript.md supplement.md cover_letter.md tripod_ai_checklist.md)
for name in "${PACKET[@]}"; do
  [ -f "$PAPER/$name" ] || { echo "no such document: $PAPER/$name" >&2; exit 1; }
done

status=0
for fmt in docx pdf; do
  echo "== .$fmt =="
  ( cd "$PAPER" && bash "$BUILD" --format "$fmt" "$@" "${PACKET[@]}" ) || status=1
  echo
done

exit $status
