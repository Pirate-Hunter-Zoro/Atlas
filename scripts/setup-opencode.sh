#!/usr/bin/env bash
# ===========================================================================
#  setup-opencode.sh -- OpenCode, DeepSeek and the parity layer on this Mac.
#
#      bash scripts/setup-opencode.sh [--dry-run] [--no-agents] [--no-contract]
#
#  What it does, in order:
#
#  1. Homebrew and Node, when missing (opencode itself is the npm global
#     `opencode-ai`, installed with Homebrew's npm).
#  2. The parity layer: `upkeep/opencode/install.py` copies the plugin, agents,
#     commands and capabilities into ~/.config/opencode and merges the managed
#     keys into opencode.jsonc. That is the whole tool surface: monitor, wakeup,
#     cron, bg_shell, background agents, forks, workflows, worktrees and the
#     browser MCP. The plugin's pinned SDK is installed beside it.
#  3. The persistent server and the shell front ends, through
#     `upkeep install --repo`: com.mikeyferguson.opencode-serve keeps wakeups,
#     monitors and jobs alive after the window closes, and `oc` (TUI) and
#     `ocrun` (one prompt) attach to it. `--no-agents` skips this.
#  4. The DeepSeek key, read from the environment, then
#     ~/.config/api-keys/deepseek_key, then ~/.config/tutor-board/keys.env,
#     then OpenCode's own auth.json. The canonical place is the first file:
#     put the key there, one line, mode 600. It is written into OpenCode's
#     auth.json and never printed.
#  5. The personal instruction contract, when `ai-config` is beside Atlas
#     (cloned there by atlas's bootstrap, or by this script with `gh`). The
#     tool layer works without it; the persona and teaching rules do not.
#     `--no-contract` skips it.
#
#  Idempotent: a second run changes nothing. It never edits upkeep/, never
#  commits, and never prints a key. Exit status is the number of problems.
# ===========================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
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

HOME="${HOME:?}"
CFG="$HOME/.config/opencode"
KEY_FILE="$HOME/.config/api-keys/deepseek_key"
KEYS_ENV="$HOME/.config/tutor-board/keys.env"
AUTH="$HOME/.local/share/opencode/auth.json"

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
if command -v opencode >/dev/null 2>&1; then
  note "opencode $(opencode --version 2>/dev/null || echo 'version unknown')"
fi

# ------------------------------------------------------------ the parity layer
say "== the parity layer"
if [ "$DRY" = 1 ]; then
  python3 "$ROOT/upkeep/opencode/install.py" --dry-run \
    || problem "the parity installer reported a problem"
else
  python3 "$ROOT/upkeep/opencode/install.py" \
    || problem "the parity installer reported a problem"
fi

if [ -f "$CFG/package.json" ] && command -v npm >/dev/null 2>&1; then
  say "== the plugin SDK"
  if [ "$DRY" = 1 ]; then
    note "would run npm install --prefix $CFG"
  else
    npm install --prefix "$CFG" --no-fund --no-audit --silent \
      || problem "the plugin SDK did not install in $CFG"
  fi
fi

# --------------------------------------------------- the server and the fronts
if [ "$AGENTS" = 1 ]; then
  say "== the persistent server, oc and the hourly upkeep"
  if [ "$DRY" = 1 ]; then
    note "would run upkeep install --repo $ROOT"
  else
    /usr/bin/python3 "$ROOT/upkeep/upkeep.py" install --repo "$ROOT" \
      || problem "upkeep install reported a problem"
  fi
else
  note "agents skipped (--no-agents): no server, no oc, no hourly run"
fi

# ------------------------------------------------------------ the contract
if [ "$CONTRACT" = 1 ]; then
  say "== the personal contract"
  if [ ! -f "$ROOT/ai-config/INSTRUCTIONS.md" ] && [ "$DRY" = 0 ] \
         && command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    login="$(gh api user --jq .login 2>/dev/null || true)"
    if [ -n "$login" ]; then
      gh repo clone "$login/ai-config" "$ROOT/ai-config" >/dev/null 2>&1 \
        && note "cloned ai-config beside Atlas"
    fi
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
    note "but the personal instructions are not installed. Clone ai-config beside"
    note "Atlas and run ai-config/scripts/install.sh, then run this again."
  fi
fi

# ------------------------------------------------------------- the DeepSeek key
say "== the DeepSeek key"
if [ "$DRY" = 1 ]; then
  if [ -f "$KEY_FILE" ] || [ -f "$KEYS_ENV" ] || [ -f "$AUTH" ] \
       || [ -n "${DEEPSEEK_API_KEY:-}" ]; then
    note "would write $AUTH from the key"
  else
    problem "no DeepSeek key: put it in $KEY_FILE, one line, mode 600"
  fi
else
  python3 - "$KEY_FILE" "$KEYS_ENV" "$AUTH" <<'PY'
import json
import os
import re
import sys

key_file, keys_env, auth = sys.argv[1:4]


def one(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip() or None
    except OSError:
        return None


def from_env_file(path):
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                m = re.match(r"^\s*(?:export\s+)?DEEPSEEK_API_KEY\s*=\s*(.*?)\s*$", line)
                if not m:
                    continue
                value = m.group(1)
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                    value = value[1:-1]
                return value or None
    except OSError:
        pass
    return None


def from_auth(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        got = data.get("deepseek") if isinstance(data, dict) else None
        return (got or {}).get("key") or None if isinstance(got, dict) else None
    except (OSError, ValueError):
        return None


key = (os.environ.get("DEEPSEEK_API_KEY", "").strip()
       or one(key_file)
       or from_env_file(keys_env)
       or from_auth(auth))
if not key:
    print("no-key")
    sys.exit(3)

if one(key_file) != key:
    os.makedirs(os.path.dirname(key_file), exist_ok=True)
    fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, (key + "\n").encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(key_file, 0o600)

data = {}
try:
    with open(auth, encoding="utf-8") as fh:
        got = json.load(fh)
    if isinstance(got, dict):
        data = got
except (OSError, ValueError):
    pass
data["deepseek"] = {"type": "api", "key": key}
os.makedirs(os.path.dirname(auth), exist_ok=True)
fd = os.open(auth, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
try:
    os.write(fd, (json.dumps(data, indent=2) + "\n").encode("utf-8"))
finally:
    os.close(fd)
os.chmod(auth, 0o600)
print("ok")
PY
  case $? in
    0)  note "wrote $AUTH (mode 600)" ;;
    3)  problem "no DeepSeek key: put it in $KEY_FILE, one line, mode 600, then run this again" ;;
    *)  problem "the key could not be written to $AUTH" ;;
  esac
fi

# ---------------------------------------------------------------- the server
if [ "$AGENTS" = 1 ] && [ "$DRY" = 0 ]; then
  TARGET="gui/$(id -u)/com.mikeyferguson.opencode-serve"
  if command -v launchctl >/dev/null 2>&1 && launchctl print "$TARGET" >/dev/null 2>&1; then
    if launchctl kickstart -k "$TARGET" >/dev/null 2>&1; then
      note "restarted the OpenCode server"
      for _ in 1 2 3 4 5 6 7 8 9 10; do
        curl -fsS -m 2 -o /dev/null http://127.0.0.1:4096/global/health 2>/dev/null \
          && break
        sleep 1
      done
      curl -fsS -m 2 -o /dev/null http://127.0.0.1:4096/global/health 2>/dev/null \
        || problem "the OpenCode server did not answer on 127.0.0.1:4096"
    else
      problem "could not restart the OpenCode server"
    fi
  else
    note "the OpenCode server agent is not loaded; log out and in, or rerun with agents"
  fi
fi

say
if [ "$problems" -eq 0 ]; then
  say "OpenCode with DeepSeek is ready."
  say "Open a new terminal (the upkeep block defines oc) and run: oc"
  say "Put the key in $KEY_FILE; this script copies it to OpenCode."
else
  say "$problems problem(s); fix them above and run this again."
fi
exit "$problems"
