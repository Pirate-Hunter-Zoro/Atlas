#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# scaffold.sh -- create a course's chapter and homework folders and .tex files.
#
#   board textbook scaffold <course> [NN ...]       chapters in chapters.tsv
#   board textbook scaffold <course> --chapter-homework [NN ...]
#                                                   and chNN-homework.tex
#   board textbook scaffold <course> --hw NN [NN ...]
#                                                   numbered homework sets
#   bash board/scripts/scaffold.sh <course-dir> ...  the same, without board
#
# Every file comes from the one template, board/tex/writeup.tex.in, with
# @@TITLE@@ and @@AUTHOR@@ filled in (the author is the course's git user.name).
# A course that sets homework per chapter (Galois-Theory) uses
# --chapter-homework; one that numbers its sets across chapters (Probability)
# uses --hw.
#
# NEVER overwrites an existing .tex file: the owner's mathematics is in them.
# ---------------------------------------------------------------------------
set -euo pipefail

[[ $# -ge 1 && -d "$1" ]] || {
  echo "usage: scaffold.sh <course-dir> [--chapter-homework] [NN ...] | --hw NN [NN ...]" >&2
  exit 2; }
ROOT="$(cd "$1" && pwd)"
shift
TSV="$ROOT/chapters.tsv"
TPL="$(cd "$(dirname "${BASH_SOURCE[0]}")/../tex" && pwd)/writeup.tex.in"
AUTHOR="$(git -C "$ROOT" config user.name 2>/dev/null || true)"

sed_safe() {  # a replacement string for sed: \, / and & taken literally
  printf '%s' "$1" | sed -e 's/[\\/&]/\\&/g'
}

render() {  # render <dest> <title>
  local dest="$1" title="$2"
  if [[ -e "$dest" ]]; then echo "  keep   ${dest#"$ROOT"/}"; return; fi
  [[ -f "$TPL" ]] || { echo "missing template: $TPL" >&2; exit 1; }
  sed -e "s/@@TITLE@@/$(sed_safe "$title")/g" \
      -e "s/@@AUTHOR@@/$(sed_safe "$AUTHOR")/g" "$TPL" > "$dest"
  echo "  create ${dest#"$ROOT"/}"
}

# --- numbered homework sets ------------------------------------------------
if [[ "${1:-}" == "--hw" ]]; then
  shift
  [[ $# -gt 0 ]] || { echo "usage: scaffold.sh <course-dir> --hw NN [NN ...]" >&2; exit 2; }
  for n in "$@"; do
    num=$(printf '%02d' "$((10#$n))")
    dir="$ROOT/homework/hw${num}"
    mkdir -p "$dir/handwritten"
    [[ -e "$dir/handwritten/.gitkeep" ]] || : > "$dir/handwritten/.gitkeep"
    echo "hw${num}"
    render "$dir/hw${num}.tex" "Homework ${num}"
  done
  exit 0
fi

# --- chapters --------------------------------------------------------------
homework=0
if [[ "${1:-}" == "--chapter-homework" ]]; then
  homework=1
  shift
fi
[[ -f "$TSV" ]] || { echo "missing chapter table: $TSV" >&2; exit 1; }

want=("$@")
selected() {
  [[ ${#want[@]} -eq 0 ]] && return 0
  local n
  for n in "${want[@]}"; do [[ "$((10#$n))" == "$((10#$1))" ]] && return 0; done
  return 1
}

while IFS=$'\t' read -r num first last slug title; do
  [[ -z "${num:-}" || "${num:0:1}" == "#" ]] && continue
  selected "$num" || continue

  dir="$ROOT/chapters/ch${num}-${slug}"
  mkdir -p "$dir/notes" "$dir/handwritten"
  [[ -e "$dir/handwritten/.gitkeep" ]] || : > "$dir/handwritten/.gitkeep"

  echo "ch${num} -- ${title}"
  render "$dir/notes/ch${num}-notes.tex" "Chapter ${num} notes — ${title}"
  if [[ $homework -eq 1 ]]; then
    mkdir -p "$dir/homework"
    render "$dir/homework/ch${num}-homework.tex" "Chapter ${num} homework — ${title}"
  fi
done < "$TSV"
