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
# and steps 5 and 6 skip tailscale serve, the DeepSeek key and port 8778.
# Step 6 asks instead for the Mac mini's tailnet name, once, and writes it as
# `host` in ~/.config/tutor-board/config.json for `board pull --materials`.
# Deleting the role file makes the next run a host again.
#
# A fresh clone or an old checkout, it does the same thing, and a second run
# changes nothing. A Mac with no Homebrew gets it first (upkeep/setup-mac.sh
# --homebrew), which asks for the password once:
#
#   1  main, fast-forward only; once, the checkouts of the retired vendor
#      submodules go, and so do retired projects that hold only caches
#   2  bootstrap: `board` on the PATH, ai-config,
#      the commit hooks, the tutor-board LaunchAgent (board/bootstrap.sh)
#   3  the machine's upkeep (upkeep/setup-mac.sh: brew, the shared Brewfile,
#      opencode, Android, Flutter, fonts, editors, kept current hourly by
#      com.mikeyferguson.upkeep), then the Brewfile and every subject's
#      environment (scripts/setup.sh), and the board's whisper model
#      (scripts/speech-model.sh)
#   4  the assistant: ai-config linked, then upkeep's opencode phase once
#      more (opencode, the parity layer, the DeepSeek key) and the OpenCode
#      server restarted when a file it reads is newer than it
#   5  tailscale serves the board on the tailnet over HTTPS
#   6  DeepSeek can take a turn (opencode, the key), the board answers on
#      8778, and board/test/tracked.py passes
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
# A bare Mac: Homebrew first, at the terminal, since its installer asks for
# the password. It lands in /opt/homebrew/bin, already on the PATH above.
if ! command -v brew >/dev/null 2>&1; then
  bash upkeep/setup-mac.sh --homebrew || exit 1
  hash -r
fi

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
# Atlas vendors nothing. A clone that once had the vendor submodules keeps
# their checkouts and git dirs after the pull drops them, and they show as
# `?? vendor/`. Once, where .gitmodules is gone and .git/modules/vendor is
# still there: drop the submodule config, then each checkout and its git dir.
# A checkout with uncommitted edits or unpushed commits is kept and named.
GIT_COMMON="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"
if [ ! -f .gitmodules ] && [ -n "$GIT_COMMON" ] && [ -d "$GIT_COMMON/modules/vendor" ] \
   && [ -z "$(git ls-files -- vendor)" ]; then
  for name in $(git config --local --name-only --get-regexp '^submodule\.vendor/' 2>/dev/null \
                | sed -E 's/^submodule\.(vendor\/.*)\.[^.]+$/\1/' | sort -u); do
    git config --local --remove-section "submodule.$name" 2>/dev/null
  done
  kept=0
  for mod in "$GIT_COMMON"/modules/vendor/*; do
    [ -d "$mod" ] || continue
    path="vendor/$(basename "$mod")"
    if [ -e "$path/.git" ] && { [ -n "$(git -C "$path" status --porcelain 2>/dev/null)" ] \
         || [ -n "$(git -C "$path" log --oneline --branches --not --remotes 2>/dev/null)" ]; }; then
      warn "$path has uncommitted edits or unpushed commits, so it was kept; delete it and $mod by hand"
      kept=1
      continue
    fi
    rm -rf "$path" "$mod" && good "deleted the retired submodule $path and its git dir"
  done
  if [ "$kept" = 0 ]; then
    rmdir "$GIT_COMMON/modules/vendor" "$GIT_COMMON/modules" vendor 2>/dev/null
  fi
fi
# Five retired projects leave leftovers behind on a clone that pulls their
# removal, and subjects.walk lists any directory under projects/ as a subject.
# One goes only when git answers that it holds no tracked file and what is
# left is caches and virtualenvs. Anything else, ignored or untracked, may be
# the owner's only copy (a manuscript, a write-up), so that directory is kept
# and named, and so is every one when git or find does not answer: an empty
# answer would read as "nothing to keep".
CACHES=(-name .venv -o -name venv -o -name __pycache__ -o -name .pytest_cache
        -o -name .mypy_cache -o -name .ruff_cache)
for p in TRD-EHR PSYCH-ASR libr-local-llm Meetings Paper-Writer; do
  [ -d "projects/$p" ] || continue
  if ! tracked="$(git ls-files -- "projects/$p" 2>/dev/null)"; then
    warn "projects/$p was kept: git did not answer whether it holds tracked files"
    continue
  fi
  if [ -n "$tracked" ]; then
    warn "projects/$p still holds tracked files, so it was kept"
    continue
  fi
  if ! own="$(find "projects/$p" \( "${CACHES[@]}" \) -prune \
                -o ! -type d ! -name .DS_Store ! -name '*.pyc' -print 2>/dev/null)"; then
    warn "projects/$p was kept: find could not read all of it"
    continue
  fi
  if [ -n "$own" ]; then
    warn "projects/$p was kept: $(printf '%s\n' "$own" | wc -l | tr -d ' ') file(s) in it are not caches, such as $(printf '%s\n' "$own" | head -1); move what is yours out, then delete it"
    continue
  fi
  rm -rf "projects/$p" && good "deleted projects/$p, a retired project holding only caches"
done

echo "== 2. bootstrap"
bash board/bootstrap.sh 2>&1 | sed 's/^/  /'

echo "== 3. upkeep and environments"
# upkeep is the machine's, on every clone of Atlas or Media-Orchestrator: it
# installs and runs once here, then com.mikeyferguson.upkeep keeps it current.
# Its exit status counts the steps only the owner can take.
bash upkeep/setup-mac.sh >"$LOGS/upkeep.log" 2>&1
owner_steps=$?
if [ "$owner_steps" -eq 0 ]; then
  good "upkeep installed and run; see $LOGS/upkeep.log"
else
  sed -n '/^== what only you can do/,$p' "$LOGS/upkeep.log" | sed '1d; s/^/  /'
  printf '  ----  %s\n' "upkeep: $owner_steps step(s) above only you can take; see $LOGS/upkeep.log"
  problems=$((problems + owner_steps))
fi
if said="$(python3 scripts/brew-upgrade.py install 2>&1)"; then good "$said"; else warn "atlas-brew: $said"; fi
bash scripts/setup.sh 2>&1 | tee "$LOGS/setup.log" | sed 's/^/  /'
[ "${PIPESTATUS[0]}" -eq 0 ] || warn "scripts/setup.sh: a FAILED line above names its log"
# The board's local listener: one whisper model, checksummed, fetched once.
if [ "$CODING" = 1 ]; then
  good "skipped the whisper model: a coding checkout serves no board"
else
  bash scripts/speech-model.sh 2>&1 | sed 's/^/  /'
  [ "${PIPESTATUS[0]}" -eq 0 ] || warn "the whisper model: the line above says why"
fi

echo "== 4. the assistant"
# DeepSeek through opencode is the AI. ai-config links its contract and
# settings and loads the daily audit. Step 3's upkeep run installed node,
# opencode, the parity layer and the key; the one thing a person adds is the
# key, at ~/.config/api-keys/deepseek_key. `upkeep.py opencode` runs that phase
# once more and prints `changed: N` (files the OpenCode server reads that it
# changed), `stale: M` (files newer than the running server, such as step 3's)
# and a `problem:` line for each problem. The server restarts only when N or
# M is above 0, because a restart ends its running sessions.
if [ -f ai-config/scripts/install.sh ]; then
  # ai-config is its own repository and Atlas's pull never moves it.
  GIT_TERMINAL_PROMPT=0 git -C ai-config pull -q --ff-only origin main 2>"$LOGS/ai-config-pull.log" \
    && good "ai-config at $(git -C ai-config log -1 --format=%h)" \
    || warn "ai-config would not fast-forward (local commits or edits); see $LOGS/ai-config-pull.log"
  bash ai-config/scripts/install.sh >"$LOGS/ai-config-install.log" 2>&1 \
    && good "ai-config linked (contract, settings, daily audit)" \
    || warn "ai-config's install.sh failed; see $LOGS/ai-config-install.log"
else
  warn "no ai-config here; bootstrap clones it, then rerun"
fi
# OpenCode makes this directory on its first start. Made now, the key sync
# writes OpenCode's copy of the key into it, so the server has it from then.
mkdir -p -m 700 "$HOME/.local/share/opencode"
/usr/bin/python3 upkeep/upkeep.py opencode >"$LOGS/opencode.log" 2>&1
opencode_exit=$?
changed="$(sed -n 's/^changed: //p' "$LOGS/opencode.log" | tail -1)"
stale="$(sed -n 's/^stale: //p' "$LOGS/opencode.log" | tail -1)"
case "$changed" in
  ''|*[!0-9]*) warn "upkeep.py opencode did not say what changed (exit $opencode_exit); see $LOGS/opencode.log"
               changed=0 ;;
esac
case "$stale" in ''|*[!0-9]*) stale=0 ;; esac
# A missing DeepSeek key is already one of step 3's owner steps; it counts once.
key_named=""
grep -q 'Put the DeepSeek API key' "$LOGS/upkeep.log" 2>/dev/null && key_named=1
key_missing=""
opencode_problems=0
while IFS= read -r line; do
  case "$line" in
    "no DeepSeek key"*) key_missing=1; [ -n "$key_named" ] && continue ;;
  esac
  warn "$line"
  opencode_problems=$((opencode_problems + 1))
done < <(sed -n 's/^problem: //p' "$LOGS/opencode.log")
if [ "$opencode_problems" -gt 0 ]; then
  printf '  ----  %s\n' "upkeep's opencode phase: the line(s) above; see $LOGS/opencode.log"
elif [ -n "$key_missing" ]; then
  good "opencode and the parity layer ($changed change(s)); the DeepSeek key is step 3's owner step"
else
  good "opencode, the DeepSeek key and the parity layer ($changed change(s)); see $LOGS/opencode.log"
fi
if v="$(opencode --version 2>/dev/null)" && [ -n "$v" ]; then
  good "opencode $v"
else
  warn "opencode does not run (opencode --version); see $LOGS/opencode.log"
fi
SERVE="gui/$(id -u)/com.mikeyferguson.opencode-serve"
serve_answers() { curl -fsS -m 2 -o /dev/null http://127.0.0.1:4096/global/health 2>/dev/null; }
if [ "$changed" -gt 0 ]; then
  why="$changed file(s) it reads changed"
else
  why="$stale file(s) it reads are newer than it"
fi
if ! launchctl print "$SERVE" >/dev/null 2>&1; then
  if [ "$changed" -gt 0 ] || [ "$stale" -gt 0 ]; then
    warn "the OpenCode server agent is not loaded, and $why; log out and in, then rerun"
  fi
else
  if [ "$changed" -eq 0 ] && [ "$stale" -eq 0 ]; then
    good "the OpenCode server left running: nothing it reads changed"
  elif launchctl kickstart -k "$SERVE" >/dev/null 2>&1; then
    good "restarted the OpenCode server: $why"
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      serve_answers && break
      sleep 1
    done
  else
    warn "could not restart the OpenCode server ($SERVE)"
  fi
  if serve_answers; then
    good "the OpenCode server answers on 127.0.0.1:4096"
  else
    warn "the OpenCode server does not answer on 127.0.0.1:4096; see ~/.local/state/opencode/serve.log"
  fi
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
  good "skipped the DeepSeek key and port 8778: the board runs on the Mac mini"
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
  # The board's own readiness check, so this line and a turn never disagree:
  # opencode on the PATH, the DeepSeek key readable, the allowance not spent.
  if said="$(cd board && python3 -c 'import sys
sys.path.insert(0, ".")
from tutorboard.agents import recipes
why = recipes.ready()
print(why or "")
sys.exit(1 if why else 0)' 2>&1)"; then
    good "DeepSeek can take a turn: opencode is here and the key is readable"
  else
    warn "DeepSeek cannot take a turn: $said (README, Setting up the Mac)"
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

echo
if [ "$problems" -eq 0 ] && [ "$CODING" = 1 ]; then
  echo "THIS CODING CHECKOUT IS UP TO DATE. Run the command a session's header shows: board code <session-id> <paths>."
elif [ "$problems" -eq 0 ]; then
  echo "THE MAC IS UP TO DATE. On the iPad: the tailnet address in Safari, Share, Add to Home Screen."
else
  echo "$problems thing(s) above still need a person."
fi
exit "$problems"
