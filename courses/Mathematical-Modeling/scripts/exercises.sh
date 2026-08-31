#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# exercises.sh -- print a lesson's exercise notebook as a submission PDF.
#
#   ./scripts/exercises.sh 01           one lesson
#   ./scripts/exercises.sh 01 02 07     several, in one kernel session
#   ./scripts/exercises.sh all          every lesson that has an exercise notebook
#   ./scripts/exercises.sh --tex 01     force the no-kernel route
#
# The submission format for this course is a printed notebook with the output
# cleared, not a .nb file (README, "Submission format"). There are two ways to
# produce one and they are not equal:
#
#   1. WOLFRAM (scripts/nb2pdf.wls) -- the real thing. The notebook's own styles,
#      and its two-dimensional typeset input drawn as a built-up fraction rather
#      than respelled. Needs an ACTIVATED Engine, which is per-machine and has to
#      be done interactively once (WOLFRAM-LICENSE.md).
#
#   2. LATEX (scripts/nb2tex.py) -- needs no kernel whatsoever. Same content,
#      typeset as a LaTeX document instead of as a notebook, with the 2-D forms
#      written linearly. This is what a machine with no activated Engine gets,
#      and it is the difference between having a submission and not having one.
#
# Wolfram is tried first and LaTeX is the fallback, decided by whether the run
# actually succeeds rather than by guessing at the licence state -- asking costs
# a kernel start, which is most of the total time.
#
# Every notebook is passed to ONE wolframscript invocation. The kernel takes the
# better part of a minute to start; sixteen invocations cost sixteen startups.
# ---------------------------------------------------------------------------
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

FORCE_TEX=0
nums=()
for a in "$@"; do
  case "$a" in
    --tex) FORCE_TEX=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    all) for d in lessons/lesson-*; do
           ls "$d"/work/*Exercises*.nb >/dev/null 2>&1 && nums+=("${d##*lesson-}")
         done ;;
    *) nums+=("$a") ;;
  esac
done
[ "${#nums[@]}" -gt 0 ] || { echo "usage: exercises.sh [--tex] NN [NN ...] | all" >&2; exit 2; }

pairs=(); missing=0
for n in "${nums[@]}"; do
  nb="$(ls "lessons/lesson-$n/work/"*Exercises*.nb 2>/dev/null | head -1)"
  if [ -z "$nb" ]; then
    echo "no exercise notebook in lessons/lesson-$n/work/" >&2
    missing=1; continue
  fi
  mkdir -p "lessons/lesson-$n/build"
  pairs+=("$nb" "lessons/lesson-$n/build/lesson-$n-exercises.pdf")
done
[ "${#pairs[@]}" -gt 0 ] || exit 1

if [ "$FORCE_TEX" = 0 ] && command -v wolframscript >/dev/null 2>&1; then
  echo "printing $(( ${#pairs[@]} / 2 )) notebook(s) through Wolfram"
  if wolframscript -file "$ROOT/scripts/nb2pdf.wls" "${pairs[@]}" </dev/null; then
    exit "$missing"
  fi
  echo "Wolfram could not print them (an unactivated Engine does this);"
  echo "falling back to the LaTeX route, which needs no kernel."
fi

# --- the no-kernel route ---------------------------------------------------
rc=$missing
for n in "${nums[@]}"; do
  nb="$(ls "lessons/lesson-$n/work/"*Exercises*.nb 2>/dev/null | head -1)"
  [ -n "$nb" ] || continue
  tex="lessons/lesson-$n/work/lesson-$n-exercises.tex"
  python3 "$ROOT/scripts/nb2tex.py" "$nb" -o "$tex" >/dev/null || { rc=1; continue; }
  bash "$ROOT/scripts/build.sh" "$tex" || rc=1
done
exit $rc
