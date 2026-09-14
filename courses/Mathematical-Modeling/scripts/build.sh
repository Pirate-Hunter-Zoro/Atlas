#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# build.sh — compile one .tex file into its unit's build/ directory.
#
#   ./scripts/build.sh chapters/ch03-*/notes/ch03-notes.tex
#   ./scripts/build.sh chapters/ch01-*/homework/ch01-homework.tex
#
# Uses latexmk when it actually works on this machine, and falls back to a
# plain pdflatex loop otherwise (the system perl here is missing Time::HiRes,
# which breaks latexmk). Runs twice so \tableofcontents and cross-references
# settle, three times if the log still asks.
# ---------------------------------------------------------------------------
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export TEXINPUTS="$ROOT/latex:${TEXINPUTS:-}"
export PATH="$HOME/.TinyTeX/bin/x86_64-linux:$PATH"

src="${1:?usage: build.sh <file.tex>}"
[[ -f "$src" ]] || { echo "no such file: $src" >&2; exit 1; }
src="$(cd "$(dirname "$src")" && pwd)/$(basename "$src")"
base="$(basename "$src" .tex)"

# Walk up to the nearest chNN-* / lesson-NN unit directory; build there.
unit="$(dirname "$src")"
while [[ "$unit" != "$ROOT" && "$unit" != "/" ]]; do
  case "$(basename "$unit")" in
    ch[0-9]*|hw[0-9]*|lesson-[0-9]*) break ;;
  esac
  unit="$(dirname "$unit")"
done
[[ "$unit" == "$ROOT" || "$unit" == "/" ]] && unit="$(dirname "$src")"
outdir="$unit/build"
mkdir -p "$outdir"

run() {
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error \
           -output-directory="$outdir" "$src" >/dev/null 2>&1
}

if latexmk -v >/dev/null 2>&1; then
  latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error \
          -outdir="$outdir" "$src" >/dev/null 2>&1
  status=$?
else
  run; status=$?
  if [[ $status -eq 0 ]]; then
    run; status=$?
    if grep -qE 'Rerun to get|Label\(s\) may have changed' "$outdir/$base.log" 2>/dev/null; then
      run; status=$?
    fi
  fi
fi

log="$outdir/$base.log"
if [[ $status -ne 0 || ! -f "$outdir/$base.pdf" ]]; then
  echo "FAILED: ${src#"$ROOT"/}"
  grep -E '^[^ ]+\.(tex|sty):[0-9]+:|^!' "$log" 2>/dev/null | head -10
  exit 1
fi

pages=$(pdfinfo "$outdir/$base.pdf" 2>/dev/null | awk '/^Pages/{print $2}')
warnings=$(grep -cE 'LaTeX Warning|Overfull|Underfull' "$log" 2>/dev/null || true)
echo "OK: ${outdir#"$ROOT"/}/$base.pdf (${pages:-?} pages, ${warnings:-0} warnings)"
