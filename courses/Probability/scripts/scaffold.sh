#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# scaffold.sh — create chapter and homework folders with their .tex files.
#
#   ./scripts/scaffold.sh                 every chapter in chapters.tsv
#   ./scripts/scaffold.sh 03 04           only those chapters
#   ./scripts/scaffold.sh --hw 04         create homework set 04
#
# Chapters carry the reading, the lecture modules, and the notes.
# Homework sets are numbered by assignment, not by chapter, because the
# assignments cut across chapters.
#
# NEVER overwrites an existing .tex file.
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TSV="$ROOT/chapters.tsv"
TPL="$ROOT/latex/templates"

render() {  # render <template> <dest> <num> <title>
  local tpl="$1" dest="$2" num="$3" title="$4"
  if [[ -e "$dest" ]]; then echo "  keep   ${dest#"$ROOT"/}"; return; fi
  sed -e "s/@@NUM@@/$num/g" -e "s/@@TITLE@@/${title//\//\\/}/g" "$tpl" > "$dest"
  echo "  create ${dest#"$ROOT"/}"
}

# --- homework mode ---------------------------------------------------------
if [[ "${1:-}" == "--hw" ]]; then
  shift
  [[ $# -gt 0 ]] || { echo "usage: scaffold.sh --hw NN [NN ...]" >&2; exit 1; }
  for n in "$@"; do
    num=$(printf '%02d' "$((10#$n))")
    dir="$ROOT/homework/hw${num}"
    mkdir -p "$dir"/{assignment,handwritten,build}
    for sub in assignment handwritten; do
      [[ -e "$dir/$sub/.gitkeep" ]] || : > "$dir/$sub/.gitkeep"
    done
    echo "hw${num}"
    render "$TPL/homework.tex.in" "$dir/hw${num}.tex" "$num" "Homework ${num}"
  done
  exit 0
fi

# --- chapter mode ----------------------------------------------------------
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
  mkdir -p "$dir"/{reading,lectures,notes,handwritten,build}
  for sub in reading lectures handwritten; do
    [[ -e "$dir/$sub/.gitkeep" ]] || : > "$dir/$sub/.gitkeep"
  done

  echo "ch${num} — ${title}"
  render "$TPL/notes.tex.in" "$dir/notes/ch${num}-notes.tex" "$num" "$title"
done < "$TSV"
