#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# split-textbook.sh -- cut a course's textbook into per-chapter readings.
#
#   board textbook split <course> [NN ...]
#   bash board/scripts/split-textbook.sh <course-dir> [NN ...]
#
# Reads the one PDF in <course>/textbook/ and the page ranges in
# <course>/chapters.tsv (num, first_pdf_page, last_pdf_page, slug, title,
# tab-separated; `#` lines are comments). Writes
# <course>/chapters/chNN-slug/reading/chNN.pdf, overwriting: an excerpt is
# derived, and the root .gitignore keeps textbook/ and reading/ out of git.
# ---------------------------------------------------------------------------
set -euo pipefail

[[ $# -ge 1 && -d "$1" ]] || {
  echo "usage: split-textbook.sh <course-dir> [NN ...]" >&2; exit 2; }
ROOT="$(cd "$1" && pwd)"
shift
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

  # gs complains about outline links pointing outside the page range, which
  # is what excerpting does, so its chatter is discarded. A failure is not.
  if ! gs -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -dQUIET -dSAFER \
       -dFirstPage="$first" -dLastPage="$last" \
       -sOutputFile="$out" "$SRC" >/dev/null 2>&1 || [[ ! -s "$out" ]]; then
    echo "gs failed on ch${num} (pages ${first}-${last})" >&2
    exit 1
  fi

  printf 'ch%s  pp.%s-%s  %-52s -> %s\n' \
    "$num" "$first" "$last" "$title" "${out#"$ROOT"/}"
  made=$((made + 1))
done < "$TSV"

echo "$made chapter excerpt(s) written."
