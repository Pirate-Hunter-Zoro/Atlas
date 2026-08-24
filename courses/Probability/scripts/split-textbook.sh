#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# split-textbook.sh — cut the full textbook into per-chapter excerpts.
#
#   ./scripts/split-textbook.sh          all chapters listed in chapters.tsv
#   ./scripts/split-textbook.sh 07 12    only those chapters
#
# Output: chapters/chNN-slug/reading/chNN.pdf
# Existing excerpts are overwritten; they are derived artifacts and git-ignored.
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TSV="$ROOT/chapters.tsv"

# The one PDF in textbook/ is the source text.
shopt -s nullglob
srcs=("$ROOT"/textbook/*.pdf)
shopt -u nullglob
(( ${#srcs[@]} == 1 )) || {
  echo "expected exactly one PDF in $ROOT/textbook/, found ${#srcs[@]}" >&2; exit 1; }
SRC="${srcs[0]}"

[[ -f "$TSV" ]] || { echo "missing chapter table: $TSV" >&2; exit 1; }
command -v gs >/dev/null || { echo "ghostscript (gs) not found" >&2; exit 1; }

want=("$@")
selected() {
  [[ ${#want[@]} -eq 0 ]] && return 0
  local n
  for n in "${want[@]}"; do [[ "$n" == "$1" || "$((10#$n))" == "$((10#$1))" ]] && return 0; done
  return 1
}

made=0
while IFS=$'\t' read -r num first last slug title; do
  [[ -z "${num:-}" || "${num:0:1}" == "#" ]] && continue
  selected "$num" || continue

  dir="$ROOT/chapters/ch${num}-${slug}/reading"
  mkdir -p "$dir"
  out="$dir/ch${num}.pdf"

  # gs complains loudly about outline links pointing outside the page range;
  # that is exactly what excerpting does, so the chatter is discarded.
  gs -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -dQUIET -dSAFER \
     -dFirstPage="$first" -dLastPage="$last" \
     -sOutputFile="$out" "$SRC" >/dev/null 2>&1

  printf 'ch%s  pp.%s-%s  %-52s -> %s\n' \
    "$num" "$first" "$last" "$title" "${out#"$ROOT"/}"
  made=$((made + 1))
done < "$TSV"

echo "$made chapter excerpt(s) written."
