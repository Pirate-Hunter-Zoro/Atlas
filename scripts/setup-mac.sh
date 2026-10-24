#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup-mac.sh -- make this Mac the Atlas host, fully up to date.
#
#     cd ~/Developer/Atlas && bash scripts/setup-mac.sh
#     cd ~/Developer/Atlas && bash scripts/setup-mac.sh --coding
#
# --coding makes a coding checkout instead, a laptop that runs `board code` and
# no board: it writes `coding` to ~/.config/tutor-board/role, so every rerun
# stays one, and then step 2 installs no board LaunchAgent and boots out a stray one,
# and steps 5 and 6 skip tailscale serve, the provider config and port 8778.
# Step 6 asks instead for the Mac mini's tailnet name, once, and writes it as
# `host` in ~/.config/tutor-board/config.json for `board pull --materials`.
# Deleting the role file makes the next run a host again.
#
# A fresh clone or an old checkout, it does the same thing, and a second run
# changes nothing:
#
#   1  main, fast-forward only
#   2  bootstrap: `board` on the PATH, the vendored submodules, ai-config,
#      the commit hooks, the tutor-board LaunchAgent (board/bootstrap.sh)
#   3  the Brewfile and every subject's environment (scripts/setup.sh)
#   4  the assistant CLIs: ai-config linked, and every CLI its descriptors know
#      how to install, installed when missing (none is required); and
#      ai-config/policy/phi.py is there, since without it `board code`
#      withholds every check's output from the tutor
#   5  tailscale serves the board on the tailnet over HTTPS
#   6  the provider config exists, the board answers on 8778, and
#      board/test/tracked.py passes
#   7  brew upkeep: the atlas.brew-upgrade LaunchAgent, both roles (scripts/brew-upgrade.py)
#
# It never stops at the first problem. Each line says ok or ----, and the last
# line counts what still needs a person. Logs: ~/.local/state/atlas-setup/.
# ---------------------------------------------------------------------------
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="${XDG_STATE_HOME:-$HOME/.local/state}/atlas-setup"
mkdir -p "$LOGS"
cd "$ROOT" || exit 1
for d in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin"; do
  case ":$PATH:" in *":$d:"*) ;; *) PATH="$d:$PATH" ;; esac
done
export PATH

problems=0
good() { printf '  ok    %s\n' "$*"; }
warn() { printf '  ----  %s\n' "$*"; problems=$((problems + 1)); }

[ "$(uname -s)" = Darwin ] \
  || { echo "this is not a Mac; Atlas runs on a Mac only."; exit 1; }
command -v brew >/dev/null 2>&1 \
  || { echo "no Homebrew. Install it from https://brew.sh, then rerun."; exit 1; }

# The role is read by board/install.sh and board/bootstrap.sh too.
ROLE_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/tutor-board/role"
case "${1:-}" in
  "") ;;
  --coding) mkdir -p "$(dirname "$ROLE_FILE")" && printf 'coding\n' >"$ROLE_FILE" ;;
  *) echo "unknown option: $1 (the one option is --coding)"; exit 1 ;;
esac
CODING=0
[ "$(tr -d '[:space:]' <"$ROLE_FILE" 2>/dev/null)" = coding ] && CODING=1
[ "$CODING" = 1 ] && echo "a coding checkout ($ROLE_FILE): no board, no board LaunchAgent, no tailscale serve"

echo "== 1. main"
if GIT_TERMINAL_PROMPT=0 git pull -q --ff-only origin main 2>"$LOGS/pull.log"; then
  good "main at $(git log -1 --oneline)"
else
  warn "git pull --ff-only refused (local commits or edits); see $LOGS/pull.log and git status"
fi

echo "== 2. bootstrap"
bash board/bootstrap.sh 2>&1 | sed 's/^/  /'

echo "== 3. environments"
bash scripts/setup.sh 2>&1 | tee "$LOGS/setup.log" | sed 's/^/  /'
[ "${PIPESTATUS[0]}" -eq 0 ] || warn "scripts/setup.sh: a FAILED line above names its log"

echo "== 4. assistant CLIs"
# None is load-bearing: a CLI that will not install is reported, never a stop.
# ai-config links each one's contract, PHI hook and settings and the shell
# block; install-clis puts in any its descriptors know how to install.
if [ -f ai-config/scripts/install.sh ]; then
  # ai-config is its own repository and Atlas's pull never moves it.
  GIT_TERMINAL_PROMPT=0 git -C ai-config pull -q --ff-only origin main 2>"$LOGS/ai-config-pull.log" \
    && good "ai-config at $(git -C ai-config log -1 --format=%h)" \
    || warn "ai-config would not fast-forward (local commits or edits); see $LOGS/ai-config-pull.log"
  bash ai-config/scripts/install.sh >"$LOGS/ai-config-install.log" 2>&1 \
    && good "ai-config linked (contract, PHI hook, settings, shell)" \
    || warn "ai-config's install.sh failed; see $LOGS/ai-config-install.log"
  [ -f ai-config/policy/phi.py ] \
    && good "ai-config/policy/phi.py is there" \
    || warn "no ai-config/policy/phi.py: without it, board code withholds every check's output from the tutor"
  bash ai-config/scripts/install-clis.sh 2>&1 | sed 's/^/  /'
  [ "${PIPESTATUS[0]}" -eq 0 ] || warn "an assistant CLI did not install; the line above says how by hand"
else
  warn "no ai-config here; bootstrap clones it, then rerun"
fi

echo "== 5. tailscale"
if [ "$CODING" = 1 ]; then
  good "skipped: a coding checkout serves no board"
elif ! command -v tailscale >/dev/null 2>&1; then
  warn "no tailscale; the Brewfile installs it, then log in with: tailscale up"
elif tailscale serve status 2>/dev/null | grep -q '127.0.0.1:8778'; then
  good "tailscale serves http://127.0.0.1:8778"
elif tailscale serve --bg --https=443 http://127.0.0.1:8778 >"$LOGS/tailscale.log" 2>&1; then
  good "tailscale now serves http://127.0.0.1:8778 over HTTPS"
else
  warn "tailscale serve failed (logged in? tailscale up); see $LOGS/tailscale.log"
fi

echo "== 6. checks"
if [ "$CODING" = 1 ]; then
  good "skipped the provider config and port 8778: the board runs on the Mac mini"
  # `host` in config.json: read it, else ask once and merge it in. The other
  # keys are kept; a config.json that is not JSON is left alone.
  CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/tutor-board/config.json"
  HOST_PY='
import json, os, re, sys
path = sys.argv[1]
try:
    with open(path) as fh:
        cfg = json.load(fh)
except OSError:
    cfg = {}
except ValueError:
    sys.exit("%s is not JSON, so host was not written" % path)
if not isinstance(cfg, dict):
    sys.exit("%s is not a JSON object, so host was not written" % path)
if len(sys.argv) < 3:
    print(str(cfg.get("host") or "").strip())
    sys.exit(0)
host = sys.argv[2].strip()
if not re.match(r"^(?:[A-Za-z0-9._-]+@)?[A-Za-z0-9][A-Za-z0-9.-]*$", host):
    sys.exit("%r is not a host name, so host was not written" % host)
cfg["host"] = host
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path + ".tmp", "w") as fh:
    json.dump(cfg, fh, indent=2)
    fh.write("\n")
os.replace(path + ".tmp", path)
'
  host="$(python3 -c "$HOST_PY" "$CONFIG" 2>/dev/null || true)"
  if [ -z "$host" ]; then
    answer=""
    read -r -p "  the Mac mini's tailnet name, for board pull --materials (blank: later): " answer || true
    if [ -n "$answer" ] && said="$(python3 -c "$HOST_PY" "$CONFIG" "$answer" 2>&1)"; then
      host="$answer"
    elif [ -n "$answer" ]; then
      warn "$said"
    fi
  fi
  answer="${answer:-}"
  if [ -n "$host" ]; then
    good "board pull --materials copies from $host (config.json host)"
  elif [ -z "$answer" ]; then
    warn "no host in $CONFIG: board pull --materials refuses until a rerun is given the Mac mini's tailnet name"
  fi
else
  if [ -f "$HOME/.config/tutor-board/config.json" ]; then
    good "~/.config/tutor-board/config.json is there"
  else
    warn "no ~/.config/tutor-board/config.json: set provider, fallback and vision_agent (README, Setting up the Mac)"
  fi
  code=""
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:8778/ || true)"
    [ "$code" = 200 ] && break
    sleep 2
  done
  if [ "$code" = 200 ]; then
    good "the board answers on 127.0.0.1:8778"
  else
    warn "the board does not answer on 8778; see ~/.local/state/tutor-board/server.log"
  fi
fi
python3 board/test/tracked.py >"$LOGS/tracked.log" 2>&1 \
  && good "tracked.py: git can see nothing it must not" || warn "tracked.py fails; see $LOGS/tracked.log"

echo "== 7. brew upkeep"
if said="$(python3 scripts/brew-upgrade.py install 2>&1)"; then good "$said"; else warn "brew upkeep: $said"; fi

echo
if [ "$problems" -eq 0 ] && [ "$CODING" = 1 ]; then
  echo "THIS CODING CHECKOUT IS UP TO DATE. Run the command a session's header shows: board code <session-id> <paths>."
elif [ "$problems" -eq 0 ]; then
  echo "THE MAC IS UP TO DATE. On the iPad: the tailnet address in Safari, Share, Add to Home Screen."
else
  echo "$problems thing(s) above still need a person."
fi
exit "$problems"
