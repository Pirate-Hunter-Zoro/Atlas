#!/usr/bin/env bash
# ===========================================================================
#  setup-opencode.sh -- OpenCode, DeepSeek and the parity layer on this Mac.
#
#      bash scripts/setup-opencode.sh [--dry-run] [--no-agents] [--no-contract]
#
#  scripts/setup-mac.sh runs it in its step 4; run it alone to redo only the
#  assistant. It is a thin entry to upkeep, which keeps all of it current:
#
#  1. Homebrew, Node and opencode (the npm global `opencode-ai`), when missing.
#  2. `upkeep install --repo <Atlas>`: the hourly upkeep, the opencode doctor,
#     the persistent server com.mikeyferguson.opencode-serve, and `oc`/`ocrun`
#     through ~/.zprofile. `--no-agents` skips it and the restart.
#  3. `upkeep opencode`: upkeep's opencode phase alone. The doctor, the
#     DeepSeek key sync (its one key order, upkeep/README.md), the parity
#     layer (upkeep/opencode/install.py) and the plugin's pinned packages.
#  4. The personal contract, ai-config, cloned with `gh` when missing.
#     `--no-contract` skips it.
#  5. The server restarts only when a file it reads changed: in step 3, or
#     after it started (an hourly run, or setup-mac.sh's own upkeep run,
#     installs without restarting it). A restart kills its running sessions.
#  6. Checks: opencode runs, the plugin is installed, the server answers.
#
#  A second run changes nothing and restarts nothing. `--dry-run` writes
#  nothing and says what it would do. It never prints a key. Exit status is
#  the number of problems.
# ===========================================================================
set -uo pipefail

DRY=0
AGENTS=1
CONTRACT=1
for arg in "$@"; do
  case "$arg" in
    --dry-run)     DRY=1 ;;
    --no-agents)   AGENTS=0 ;;
    --no-contract) CONTRACT=0 ;;
    -h|--help)
      awk 'NR < 3 {next} /^# ===/ {exit} {sub(/^#  ?/, ""); print}' "${BASH_SOURCE[0]}"
      exit 0 ;;
    *) echo "unknown option: $arg (--dry-run, --no-agents, --no-contract)" >&2
       exit 2 ;;
  esac
done

say()  { printf '%s\n' "$*"; }
note() { printf '  %s\n' "$*"; }

problems=0
problem() {
  printf 'problem: %s\n' "$*" >&2
  problems=$((problems + 1))
}

[ "$(uname -s)" = Darwin ] || { echo "setup-opencode.sh: this is a Mac only" >&2; exit 1; }

ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)"
[ -n "$ROOT" ] && [ -f "$ROOT/upkeep/upkeep.py" ] \
  || { echo "setup-opencode.sh: run it from a clone of Atlas" >&2; exit 1; }
HOME="${HOME:?}"
CFG="$HOME/.config/opencode"
UPKEEP="$ROOT/upkeep/upkeep.py"
SERVE="gui/$(id -u)/com.mikeyferguson.opencode-serve"
AI_CONFIG_REPO="Pirate-Hunter-Zoro/ai-config"

# A login shell and launchd hand over a short PATH; the tools live here.
for d in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin"; do
  case ":$PATH:" in *":$d:"*) ;; *) PATH="$PATH:$d" ;; esac
done
export PATH

# ---------------------------------------------------------------- Homebrew
if ! command -v brew >/dev/null 2>&1; then
  say "== Homebrew (it asks for your password once)"
  if [ "$DRY" = 1 ]; then
    note "would install Homebrew with upkeep/setup-mac.sh --homebrew"
  else
    bash "$ROOT/upkeep/setup-mac.sh" --homebrew \
      || problem "Homebrew could not be installed; install it, then run this again"
    for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
      [ -x "$b" ] && eval "$("$b" shellenv)" && break
    done
  fi
fi

# --------------------------------------------------------------------- Node
if ! command -v npm >/dev/null 2>&1; then
  say "== node (npm carries opencode)"
  if [ "$DRY" = 1 ]; then
    note "would run brew install node"
  elif command -v brew >/dev/null 2>&1; then
    brew install node || problem "node could not be installed"
  else
    problem "npm is missing and there is no brew to install node"
  fi
fi

# ----------------------------------------------------------------- OpenCode
if ! command -v opencode >/dev/null 2>&1; then
  say "== opencode (the opencode-ai npm package)"
  if [ "$DRY" = 1 ]; then
    note "would run npm install -g opencode-ai --foreground-scripts --allow-scripts=opencode-ai"
  elif command -v npm >/dev/null 2>&1; then
    npm install -g opencode-ai --foreground-scripts --allow-scripts=opencode-ai \
      || problem "opencode could not be installed with npm"
    hash -r 2>/dev/null || true
    command -v opencode >/dev/null 2>&1 \
      || problem "opencode was installed but is not on PATH; find it with npm prefix -g"
  else
    problem "opencode is missing and npm is not here"
  fi
fi

# ------------------------------------------------------------------- upkeep
if [ "$AGENTS" = 1 ]; then
  say "== upkeep: the hourly run, the doctor, the server, oc"
  if [ "$DRY" = 1 ]; then
    note "would run upkeep install --repo $ROOT"
  else
    said="$(/usr/bin/python3 "$UPKEEP" install --repo "$ROOT" 2>&1)"
    code=$?
    while IFS= read -r line; do
      [ -n "$line" ] && note "$line"
    done <<<"$said"
    [ "$code" -eq 0 ] || problem "upkeep install reported a problem (above)"
  fi
else
  note "agents skipped (--no-agents): no server, no oc, no hourly run"
fi

# ------------------------------------------- upkeep's opencode phase, alone
say "== the opencode phase: doctor, DeepSeek key, parity layer"
# OpenCode makes this directory on its first start. The key is written into
# it now, so the server has the key from that start.
if [ "$DRY" = 1 ]; then
  said="$(/usr/bin/python3 "$UPKEEP" opencode --dry-run 2>&1)"
else
  mkdir -p -m 700 "$HOME/.local/share/opencode"
  said="$(/usr/bin/python3 "$UPKEEP" opencode 2>&1)"
fi
code=$?
changed=""
stale=0
while IFS= read -r line; do
  case "$line" in
    "changed: "*) changed="${line#changed: }" ;;
    "stale: "*) stale="${line#stale: }" ;;
    "problem: "*) problem "${line#problem: }" ;;
    "") ;;
    *) note "$line" ;;
  esac
done <<<"$said"
case "$changed" in
  ''|*[!0-9]*) problem "upkeep opencode did not say what changed (exit $code)"
               changed=0 ;;
esac
case "$stale" in ''|*[!0-9]*) stale=0 ;; esac
[ "$changed" -eq 0 ] && note "nothing changed"

# ------------------------------------------------------------ the contract
if [ "$CONTRACT" = 1 ]; then
  say "== the personal contract"
  if [ ! -f "$ROOT/ai-config/INSTRUCTIONS.md" ] && [ "$DRY" = 0 ] \
         && command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    gh repo clone "$AI_CONFIG_REPO" "$ROOT/ai-config" -- -q >/dev/null 2>&1 \
      && note "cloned ai-config beside Atlas"
  fi
  if [ -f "$ROOT/ai-config/INSTRUCTIONS.md" ] \
         && [ -f "$ROOT/ai-config/scripts/install.sh" ]; then
    if [ "$DRY" = 1 ]; then
      note "would run ai-config/scripts/install.sh (links AGENTS.md and the audit)"
    else
      bash "$ROOT/ai-config/scripts/install.sh" >/dev/null \
        || problem "ai-config/scripts/install.sh reported a problem"
      [ -L "$CFG/AGENTS.md" ] || [ -f "$CFG/AGENTS.md" ] \
        || problem "the contract is not at $CFG/AGENTS.md"
    fi
  elif [ -e "$CFG/AGENTS.md" ]; then
    note "using the existing $CFG/AGENTS.md"
  else
    note "ai-config is not here and could not be cloned; the tool layer is complete,"
    note "but the personal instructions are not installed. Clone $AI_CONFIG_REPO"
    note "beside Atlas and run ai-config/scripts/install.sh, then run this again."
  fi
fi

# ---------------------------------------------------------------- the server
serve_loaded() {
  command -v launchctl >/dev/null 2>&1 && launchctl print "$SERVE" >/dev/null 2>&1
}
healthy() {
  curl -fsS -m 2 -o /dev/null http://127.0.0.1:4096/global/health 2>/dev/null
}
if [ "$AGENTS" = 1 ]; then
  say "== the OpenCode server"
  if [ "$changed" -gt 0 ]; then
    why="$changed file(s) it reads changed"
    [ "$DRY" = 1 ] && why="$changed file(s) it reads would change"
  else
    why="$stale file(s) it reads are newer than it"
  fi
  if [ "$changed" -eq 0 ] && [ "$stale" -eq 0 ]; then
    note "left running: nothing it reads changed"
  elif [ "$DRY" = 1 ]; then
    note "would restart the OpenCode server: $why"
  elif serve_loaded; then
    if launchctl kickstart -k "$SERVE" >/dev/null 2>&1; then
      note "restarted the OpenCode server: $why"
      for _ in 1 2 3 4 5 6 7 8 9 10; do
        healthy && break
        sleep 1
      done
    else
      problem "could not restart the OpenCode server"
    fi
  else
    note "the OpenCode server agent is not loaded; log out and in, then run this again"
  fi
fi

# ----------------------------------------------------------------- checks
if [ "$DRY" = 0 ]; then
  say "== checks"
  if v="$(opencode --version 2>/dev/null)" && [ -n "$v" ]; then
    note "opencode $v"
  else
    problem "opencode does not run (opencode --version)"
  fi
  if [ -f "$CFG/plugins/parity.ts" ] && [ -f "$CFG/capabilities.md" ]; then
    note "the parity plugin and capabilities are in $CFG"
  else
    problem "the parity layer is not in $CFG"
  fi
  if [ "$AGENTS" = 1 ] && serve_loaded; then
    if healthy; then
      note "the OpenCode server answers on 127.0.0.1:4096"
    else
      problem "the OpenCode server does not answer on 127.0.0.1:4096"
    fi
  fi
fi

say
if [ "$problems" -eq 0 ]; then
  say "OpenCode with DeepSeek is ready. Open a new terminal (the upkeep block defines oc) and run: oc"
else
  say "$problems problem(s); fix them above and run this again."
fi
exit "$problems"
