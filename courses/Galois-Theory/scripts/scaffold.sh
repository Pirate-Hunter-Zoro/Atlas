#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# scaffold.sh — create chapter folders and .tex files from the templates.
#
#   ./scripts/scaffold.sh          every chapter in chapters.tsv
#   ./scripts/scaffold.sh 07 12    only those chapters
#
# NEVER overwrites an existing .tex file. The user's mathematics lives in
# those files; clobbering them is unforgivable.
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TSV="$ROOT/chapters.tsv"
TPL="$ROOT/latex/templates"

[[ -f "$TSV" ]] || { echo "missing chapter table: $TSV" >&2; exit 1; }

want=("$@")
selected() {
  [[ ${#want[@]} -eq 0 ]] && return 0
  local n
  for n in "${want[@]}"; do [[ "$((10#$n))" == "$((10#$1))" ]] && return 0; done
  return 1
}

render() {  # render <template> <dest> <num> <title>
  local tpl="$1" dest="$2" num="$3" title="$4"
  if [[ -e "$dest" ]]; then
    echo "  keep   ${dest#"$ROOT"/}"
    return
  fi
  sed -e "s/@@NUM@@/$num/g" -e "s/@@TITLE@@/${title//\//\\/}/g" "$tpl" > "$dest"
  echo "  create ${dest#"$ROOT"/}"
}

while IFS=$'\t' read -r num first last slug title; do
  [[ -z "${num:-}" || "${num:0:1}" == "#" ]] && continue
  selected "$num" || continue

  dir="$ROOT/chapters/ch${num}-${slug}"
  mkdir -p "$dir"/{reading,notes,homework,handwritten,build}
  for sub in reading handwritten; do
    [[ -e "$dir/$sub/.gitkeep" ]] || : > "$dir/$sub/.gitkeep"
  done

  echo "ch${num} — ${title}"
  render "$TPL/notes.tex.in"    "$dir/notes/ch${num}-notes.tex"       "$num" "$title"
  render "$TPL/homework.tex.in" "$dir/homework/ch${num}-homework.tex" "$num" "$title"
done < "$TSV"
