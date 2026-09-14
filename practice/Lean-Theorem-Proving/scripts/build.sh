#!/usr/bin/env bash
# Build the package and report in plain English.
#   ./scripts/build.sh            everything
#   ./scripts/build.sh Exercises.Sets.E01_InterComm    one module
#
# It also answers to a `.tex` path, because Tutor-Board's `board export --build`
# and `board hw build` call `scripts/build.sh <file.tex>` on any repository that
# has one and do not know this is a Lean package. Without the branch below that
# path became `lake build /…/lesson.tex`, which fails with a Lean error about an
# unknown target — a confusing way to say "your PDF was never made".
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/.elan/bin:$PATH"
cd "$ROOT" || exit 1

# --- a .tex argument is a board export, not a Lean target ------------------
if [[ "${1:-}" == *.tex ]]; then
  src="$1"
  [[ -f "$src" ]] || { echo "no such file: $src" >&2; exit 1; }
  src="$(cd "$(dirname "$src")" && pwd)/$(basename "$src")"
  base="$(basename "$src" .tex)"
  outdir="$(dirname "$src")"
  run() {
    pdflatex -interaction=nonstopmode -halt-on-error -file-line-error \
             -output-directory="$outdir" "$src" >/dev/null 2>&1
  }
  run; status=$?
  # Twice, so \tableofcontents and cross-references settle; a third time only
  # when the log actually asks for it.
  if [[ $status -eq 0 ]]; then
    run; status=$?
    if grep -qE 'Rerun to get|Label\(s\) may have changed' "$outdir/$base.log" 2>/dev/null; then
      run; status=$?
    fi
  fi
  if [[ $status -ne 0 || ! -f "$outdir/$base.pdf" ]]; then
    echo "FAILED: $src"
    grep -E '^[^ ]+\.(tex|sty):[0-9]+:|^!' "$outdir/$base.log" 2>/dev/null | head -10
    exit 1
  fi
  pages=$(pdfinfo "$outdir/$base.pdf" 2>/dev/null | awk '/^Pages/{print $2}')
  echo "OK: $outdir/$base.pdf (${pages:-?} pages)"
  exit 0
fi

# --- the ordinary case: a Lean build ---------------------------------------
out=$(lake build "$@" 2>&1); status=$?
# Lean writes this with BACKTICKS -- declaration uses `sorry` -- not with the
# straight quotes this used to match. Nothing matched, so every sorry warning
# was printed as though it were a real problem AND the count came out as zero:
# "BUILD OK - 0 declaration(s) still using sorry" on a package where all 26 were
# open. That is the exact "it built" / "it is proved" confusion the README warns
# about, produced by the tool meant to prevent it. Match either quoting.
SORRY="declaration uses [\`']sorry[\`']"
echo "$out" | grep -E "^(error|warning):" | grep -Ev "$SORRY" | head -20
if [[ $status -eq 0 ]]; then
  n=$(echo "$out" | grep -Ec "$SORRY")
  echo "BUILD OK — $n declaration(s) still using sorry."
else
  echo "BUILD FAILED (exit $status)."
  echo "$out" | tail -20
fi
exit $status
