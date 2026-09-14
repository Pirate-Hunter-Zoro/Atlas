#!/usr/bin/env bash
# Scaffold a new exercise and append it to the manifest.
#   ./scripts/new-exercise.sh <Topic> <ENN_Name> <decl_name> "<one-line title>"
# Writes the file with an EMPTY marked proof region. The statement is filled in
# afterwards by hand; the proof is never filled in by an assistant.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
topic="${1:?usage: new-exercise.sh Topic ENN_Name decl_name \"title\"}"
name="${2:?}"; decl="${3:?}"; title="${4:?}"
dir="$ROOT/Exercises/$topic"; mkdir -p "$dir"
f="$dir/$name.lean"
[[ -e "$f" ]] && { echo "exists: $f"; exit 1; }
cat > "$f" <<LEAN
/-!
# ${name#*_}

$title
-/

import Mathlib
import LeanTP

theorem $decl : True := by
  -- ===== PROOF: $decl =====
  -- TODO(mferguson): your proof goes here. Delete the \`sorry\` when you replace it.
  sorry
  -- ===== END PROOF: $decl =====
LEAN
next=$(grep -cv '^#' "$ROOT/exercises.tsv" | tr -d ' ')
printf '%02d\t%s\t%s\t%s\n' "$((next+1))" "$topic" "$name" "$title" >> "$ROOT/exercises.tsv"
echo "created ${f#"$ROOT"/} and appended to exercises.tsv"
