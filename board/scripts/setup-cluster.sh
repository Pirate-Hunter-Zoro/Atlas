#!/usr/bin/env bash
# ---------------------------------------------------------------------------
#  setup-cluster.sh -- put the cluster checkout right for the relay.
#
#      bash board/scripts/setup-cluster.sh
#
#  The cluster runs no board and no model: scrontab runs the relay, and that
#  is all. This bootstraps the checkout, checks ai-config is there, installs
#  the relay's scrontab entry and checks the remote answers. Idempotent; each
#  step says what it found.
# ---------------------------------------------------------------------------
set -uo pipefail

BOARD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(git -C "$BOARD" rev-parse --show-toplevel 2>/dev/null || dirname "$BOARD")"
problems=0

good() { printf '  ok    %s\n' "$*"; }
warn() { printf '  ----  %s\n' "$*"; problems=$((problems + 1)); }

echo "cluster setup: $ROOT"

# 1. bootstrap: the tools on the path, the submodules, the private repositories.
if bash "$BOARD/bootstrap.sh" >/dev/null 2>&1; then
  good "bootstrap ran"
else
  warn "bootstrap reported a problem: bash $BOARD/bootstrap.sh"
fi

# 2. ai-config: the PHI fence every hook and the relay lean on.
if [ -f "$ROOT/ai-config/policy/phi.py" ]; then
  good "ai-config is present"
else
  warn "ai-config is missing at $ROOT/ai-config; bootstrap clones it"
fi

# 3. the relay's scrontab entry.
if [ -f "$BOARD/bin/relay" ]; then
  python3 "$BOARD/bin/relay" --install || warn "the relay entry was not installed"
else
  python3 "$BOARD/bin/tutor" relay --install || warn "the relay entry was not installed"
fi

# 4. the remote: the relay pulls and pushes through it and nothing else.
if git -C "$ROOT" ls-remote origin HEAD >/dev/null 2>&1; then
  good "git ls-remote origin answers"
else
  warn "git ls-remote origin failed; check the credential on this machine"
fi

if [ "$problems" -eq 0 ]; then
  echo "The cluster is right."
else
  echo "$problems thing(s) above still need a person."
fi
exit "$problems"
