#!/bin/bash
# setup-mac.sh -- a bare Mac to a kept one, from any repo carrying upkeep/.
#
#     bash upkeep/setup-mac.sh
#     bash upkeep/setup-mac.sh --homebrew    Homebrew only, for a repo's own setup
#
# Installs Homebrew when it is missing, registers this repo with upkeep
# (`upkeep.py install --repo`), runs upkeep once with --force (brew, the
# Brewfile, opencode, Android, Flutter, fonts, VS Code and Terminal), then
# installs Xcode (mas) and the root half (sudo) when it runs at a terminal, then prints
# the steps only the owner can take. A second run changes nothing.
# Exit status: the number of owner steps still open.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
SHARE="${UPKEEP_HOME:-$HOME/.local/share/upkeep}"
APPS="${UPKEEP_APPLICATIONS:-/Applications}"
ROOT_STATUS="${UPKEEP_ROOT_STATUS:-/Library/Application Support/upkeep-root/status.json}"

[ "$(uname -s)" = Darwin ] || { echo "this is not a Mac; upkeep runs on a Mac only."; exit 1; }
case "${1:-}" in
  ""|--homebrew) ;;
  *) echo "unknown option: $1 (the one option is --homebrew)"; exit 1 ;;
esac
# Appended, never put first: the caller's PATH decides which brew runs.
for d in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin"; do
  case ":$PATH:" in *":$d:"*) ;; *) PATH="$PATH:$d" ;; esac
done
export PATH

if ! command -v brew >/dev/null 2>&1; then
  echo "== Homebrew (it asks for your password once)"
  sudo -v || { echo "Homebrew needs an administrator's password; rerun when you have it."; exit 1; }
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" \
    || { echo "the Homebrew installer failed; see above, then rerun."; exit 1; }
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    [ -x "$b" ] && eval "$("$b" shellenv)" && break
  done
fi
[ "${1:-}" = --homebrew ] && exit 0

echo "== upkeep install"
/usr/bin/python3 "$HERE/upkeep.py" install --repo "$ROOT" || echo "  upkeep install reported a problem (above)"

echo "== upkeep run --force (the first run takes a while)"
/usr/bin/python3 "$SHARE/upkeep.py" run --force
/usr/bin/python3 "$SHARE/upkeep.py" status

# At a terminal, the steps a password or an App Store sign-in can finish are taken here:
# Xcode through mas, then the root half through sudo. UPKEEP_INTERACTIVE=0 skips them,
# =1 takes them without a terminal.
interactive="${UPKEEP_INTERACTIVE:-}"
[ -n "$interactive" ] || { [ -t 0 ] && interactive=1 || interactive=0; }
if [ "$interactive" = 1 ]; then
  if [ ! -d "$APPS/Xcode.app" ] && command -v mas >/dev/null 2>&1; then
    echo "== Xcode from the App Store (signed in to the App Store, this takes a while)"
    mas get 497799835 || echo "  mas could not get Xcode; sign in to the App Store, then rerun"
  fi
  if [ -d "$APPS/Xcode.app" ] && [ ! -f "$ROOT_STATUS" ]; then
    echo "== the root half: Xcode's license and first launch, App Store auto-updates (your password)"
    sudo bash "$HERE/root/install.sh" || echo "  the root install failed (above)"
  fi
fi

steps=0
step() { steps=$((steps + 1)); printf '  %d. %s\n' "$steps" "$*"; }
echo
echo "== what only you can do"
[ -d "$APPS/Xcode.app" ] \
  || step "Install Xcode: App Store, Get (or: sudo mas get 497799835). Then step 2."
[ -f "$ROOT_STATUS" ] \
  || step "sudo bash $HERE/root/install.sh   (Xcode's license and first launch, App Store auto-updates)"
if [ -z "${DEEPSEEK_API_KEY:-}" ] && [ ! -s "$HOME/.config/api-keys/deepseek_key" ] \
   && ! grep -q '^[[:space:]]*\(export[[:space:]]*\)\{0,1\}DEEPSEEK_API_KEY=.' "$HOME/.config/tutor-board/keys.env" 2>/dev/null \
   && ! grep -q '"deepseek"' "$HOME/.local/share/opencode/auth.json" 2>/dev/null; then
  step "Put the DeepSeek API key in ~/.config/api-keys/deepseek_key (one line, chmod 600); the next run copies it everywhere."
fi
[ "$steps" -eq 0 ] && echo "  nothing: open a new terminal and this Mac is set up and kept."
exit "$steps"
