#!/usr/bin/env bash
# Build the package and report in plain English.
#   ./scripts/build.sh            everything
#   ./scripts/build.sh Exercises.Sets.E01_InterComm    one module
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/.elan/bin:$PATH"
cd "$ROOT" || exit 1
out=$(lake build "$@" 2>&1); status=$?
echo "$out" | grep -E "^(error|warning):" | grep -v "declaration uses 'sorry'" | head -20
if [[ $status -eq 0 ]]; then
  n=$(echo "$out" | grep -c "declaration uses 'sorry'")
  echo "BUILD OK — $n declaration(s) still using sorry."
else
  echo "BUILD FAILED (exit $status)."
  echo "$out" | tail -20
fi
exit $status
