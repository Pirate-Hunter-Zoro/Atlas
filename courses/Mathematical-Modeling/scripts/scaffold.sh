#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# scaffold.sh — create lesson and chapter folders with their .tex files, and
# file each instructor notebook into the unit it belongs to.
#
#   ./scripts/scaffold.sh              every unit in units.tsv
#   ./scripts/scaffold.sh lesson       just the Mathematica lessons
#   ./scripts/scaffold.sh chapter 03   just Beltrami chapter 3
#
# NEVER overwrites an existing .tex file, and never moves a notebook that has
# already been filed.
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TSV="$ROOT/units.tsv"
TPL="$ROOT/latex/templates"
DROP="$ROOT/course-materials"      # where instructor notebooks land before filing

kind_filter=""
if [[ "${1:-}" == "lesson" || "${1:-}" == "chapter" ]]; then kind_filter="$1"; shift; fi
want=("$@")

selected() {
  [[ ${#want[@]} -eq 0 ]] && return 0
  local n
  for n in "${want[@]}"; do [[ "$((10#$n))" == "$((10#$1))" ]] && return 0; done
  return 1
}

render() {  # render <template> <dest> <num> <title>
  local tpl="$1" dest="$2" num="$3" title="$4"
  if [[ -e "$dest" ]]; then echo "  keep   ${dest#"$ROOT"/}"; return; fi
  sed -e "s/@@NUM@@/$num/g" -e "s/@@TITLE@@/${title//\//\\/}/g" "$tpl" > "$dest"
  echo "  create ${dest#"$ROOT"/}"
}

file_notebooks() {  # file_notebooks <pattern> <destdir>
  # Notebook names contain spaces, so match names inside [[ ]] rather than
  # letting the shell split an unquoted glob.
  local pattern="$1" dest="$2" f name
  shopt -s nullglob
  for f in "$DROP"/*; do
    name="$(basename "$f")"
    [[ "$name" == $pattern ]] || continue
    [[ -e "$dest/$name" ]] && continue
    mv "$f" "$dest/"
    echo "  file   ${dest#"$ROOT"/}/$name"
  done
  shopt -u nullglob
}

while IFS=$'\t' read -r kind num slug title; do
  [[ -z "${kind:-}" || "${kind:0:1}" == "#" ]] && continue
  [[ -n "$kind_filter" && "$kind" != "$kind_filter" ]] && continue
  selected "$num" || continue

  if [[ "$kind" == "lesson" ]]; then
    dir="$ROOT/lessons/${slug}"
    mkdir -p "$dir"/{material,work,notes,handwritten,build}
    for sub in material work handwritten; do
      [[ -e "$dir/$sub/.gitkeep" ]] || : > "$dir/$sub/.gitkeep"
    done
    echo "lesson ${num}"
    # "Adv Lesson 0.nb" for lesson 00, "Adv Lesson NN.nb" otherwise
    file_notebooks "Adv Lesson $((10#$num)).nb" "$dir/material"
    file_notebooks "Adv Lesson ${num}.nb"       "$dir/material"
    render "$TPL/notes.tex.in" "$dir/notes/${slug}-notes.tex" "$num" "$title"
  else
    dir="$ROOT/chapters/ch${num}-${slug}"
    mkdir -p "$dir"/{material,notes,homework,handwritten,build}
    for sub in material handwritten; do
      [[ -e "$dir/$sub/.gitkeep" ]] || : > "$dir/$sub/.gitkeep"
    done
    echo "chapter ${num} — ${title}"
    file_notebooks "New Sect $((10#$num)).*.nb" "$dir/material"
    render "$TPL/notes.tex.in"    "$dir/notes/ch${num}-notes.tex"       "$num" "$title"
    render "$TPL/homework.tex.in" "$dir/homework/ch${num}-homework.tex" "$num" "$title"
  fi
done < "$TSV"

shopt -s nullglob
leftover=("$DROP"/*)
shopt -u nullglob
if (( ${#leftover[@]} )); then
  echo
  echo "unfiled in course-materials/ (${#leftover[@]}):"
  printf '  %s\n' "${leftover[@]##*/}"
fi
