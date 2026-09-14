#!/usr/bin/env bash
# Which exercises are proved and which still have holes, in manifest order.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
done_n=0; open_n=0
while IFS=$'\t' read -r num topic mod title; do
  [[ -z "${num:-}" || "${num:0:1}" == "#" ]] && continue
  f="$ROOT/Exercises/$topic/$mod.lean"
  if [[ ! -f "$f" ]]; then mark="MISSING"
  elif grep -q '^\s*sorry\s*$' "$f"; then mark="open"; open_n=$((open_n+1))
  else mark="PROVED"; done_n=$((done_n+1)); fi
  printf '%-3s %-8s %-22s %-28s %s\n' "$num" "$mark" "$topic" "$mod" "$title"
done < "$ROOT/exercises.tsv"
echo
echo "$done_n proved, $open_n open."
