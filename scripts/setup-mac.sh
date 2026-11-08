#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup-mac.sh -- make this MacBook Air the Atlas host, fully up to date.
#
#     cd ~/Developer/Atlas && bash scripts/setup-mac.sh
#
# This is the one Mac: it serves the board, runs every turn, and is the machine
# the iPad reaches. There is no second host and no coding-only checkout.
#
# A fresh clone or an old checkout, it does the same thing, and a second run
# changes nothing. A Mac with no Homebrew gets it first (upkeep/setup-mac.sh
# --homebrew), which asks for the password once:
#
#   1  main, fast-forward only; once, the checkouts of the retired vendor
#      submodules go, and so do retired projects that hold only caches
#   2  bootstrap: `board` on the PATH, ai-config,
#      the commit hooks, the tutor-board LaunchAgent (board/bootstrap.sh),
#      and the Cloudflare access refresher when a subject carries
#      `.atlas/cloudflare-access.json`
#   3  the machine's upkeep (upkeep/setup-mac.sh: brew, the shared Brewfile,
#      opencode, Android, Flutter, fonts, editors, kept current hourly by
#      com.mikeyferguson.upkeep), then the Brewfile and every subject's
#      environment (scripts/setup.sh), the board's whisper model
#      (scripts/speech-model.sh), and Comic Mono, Terminal's font
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

[ "$#" -eq 0 ] || { echo "setup-mac.sh takes no options"; exit 1; }

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

echo "== 2b. Cloudflare access"
# A subject that carries `.atlas/cloudflare-access.json` names a
# Cloudflare-protected git host. The refresher exchanges the stored
# organization token for a fresh application token and rewrites the git
# header, so only the interactive Cloudflare login is ever manual. With no
# config, no agent is left loaded.
shopt -s nullglob
cf_cfg=("$ROOT"/courses/*/.atlas/cloudflare-access.json \
        "$ROOT"/projects/*/.atlas/cloudflare-access.json)
shopt -u nullglob
CF_LABEL="com.mikeyferguson.cloudflare-access"
CF_AGENT="$HOME/Library/LaunchAgents/$CF_LABEL.plist"
if [ "${#cf_cfg[@]}" -eq 0 ]; then
  if [ -e "$CF_AGENT" ]; then
    launchctl bootout "gui/$(id -u)/$CF_LABEL" >/dev/null 2>&1
    rm -f "$CF_AGENT"
    good "no Cloudflare access config; removed the idle refresher"
  else
    good "no Cloudflare access config; nothing to refresh"
  fi
else
  mkdir -p "$(dirname "$CF_AGENT")"
  cf_tmp="$(mktemp)"
  cat >"$cf_tmp" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$CF_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>$ROOT/scripts/cloudflare-access.py</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>StartInterval</key><integer>900</integer>
  <key>ProcessType</key><string>Background</string>
  <key>LowPriorityIO</key><true/>
  <key>StandardOutPath</key><string>$LOGS/cloudflare-access.out</string>
  <key>StandardErrorPath</key><string>$LOGS/cloudflare-access.err</string>
</dict>
</plist>
PLIST
  if [ -f "$CF_AGENT" ] && cmp -s "$cf_tmp" "$CF_AGENT"; then
    rm -f "$cf_tmp"
    good "the Cloudflare access refresher is installed"
  else
    mv "$cf_tmp" "$CF_AGENT"
    launchctl bootout "gui/$(id -u)/$CF_LABEL" >/dev/null 2>&1
    good "installed the Cloudflare access refresher (every 15 minutes)"
  fi
  if ! launchctl print "gui/$(id -u)/$CF_LABEL" >/dev/null 2>&1; then
    launchctl bootstrap "gui/$(id -u)" "$CF_AGENT" >/dev/null 2>&1 \
      || warn "could not load the Cloudflare access refresher; log out and in, then rerun"
  fi
  if said="$(/usr/bin/python3 "$ROOT/scripts/cloudflare-access.py" --say 2>&1)"; then
    good "Cloudflare access: ${said:-nothing to refresh}"
  else
    warn "Cloudflare access: $said"
  fi
fi

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
bash scripts/speech-model.sh 2>&1 | sed 's/^/  /'
[ "${PIPESTATUS[0]}" -eq 0 ] || warn "the whisper model: the line above says why"
# Terminal's profile names Comic Mono. upkeep's Brewfile carries the cask, but
# a font file on disk is not enough: fontd only serves a face it registered, and
# a font that arrived after fontd started can stay unregistered, which makes
# Terminal silently fall back to its own. So the cask is installed when the file
# is missing, and fontd is restarted when the file is there but the face is not
# registered.
comic=""
for f in "$HOME"/Library/Fonts/ComicMono*.ttf /Library/Fonts/ComicMono*.ttf; do
  [ -f "$f" ] && comic=1
done
just_installed=0
if [ -z "$comic" ]; then
  if brew install --cask font-comic-mono >"$LOGS/font.log" 2>&1; then
    comic=1
    just_installed=1
  else
    warn "brew install --cask font-comic-mono failed; see $LOGS/font.log"
  fi
fi
if [ -n "$comic" ]; then
  registered=0
  if command -v atsutil >/dev/null 2>&1 \
     && atsutil fonts -list 2>/dev/null | grep -i ComicMono >/dev/null; then
    registered=1
  fi
  if [ "$registered" -eq 0 ] && command -v atsutil >/dev/null 2>&1; then
    killall fontd >/dev/null 2>&1
    sleep 2
    atsutil fonts -list 2>/dev/null | grep -i ComicMono >/dev/null && registered=1
  fi
  if [ "$registered" -eq 1 ] && [ "$just_installed" -eq 1 ]; then
    good "installed Comic Mono, Terminal's font; quit and reopen Terminal"
  elif [ "$registered" -eq 1 ]; then
    good "Comic Mono, Terminal's font, is registered"
  else
    warn "Comic Mono is on disk but macOS has not registered it; restart the Mac"
  fi
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
if ! command -v tailscale >/dev/null 2>&1; then
  warn "no tailscale; the Brewfile installs it, then log in with: tailscale up"
elif tailscale serve status 2>/dev/null | grep -q '127.0.0.1:8778'; then
  good "tailscale serves http://127.0.0.1:8778"
elif tailscale serve --bg --https=443 http://127.0.0.1:8778 >"$LOGS/tailscale.log" 2>&1; then
  good "tailscale now serves http://127.0.0.1:8778 over HTTPS"
else
  warn "tailscale serve failed (logged in? tailscale up); see $LOGS/tailscale.log"
fi

echo "== 6. checks"
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
python3 board/test/tracked.py >"$LOGS/tracked.log" 2>&1 \
  && good "tracked.py: git can see nothing it must not" || warn "tracked.py fails; see $LOGS/tracked.log"

echo
if [ "$problems" -eq 0 ]; then
  echo "THE MAC IS UP TO DATE. On the iPad: the tailnet address in Safari, Share, Add to Home Screen."
else
  echo "$problems thing(s) above still need a person."
fi
exit "$problems"
