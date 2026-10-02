#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# install.sh -- put `board` on the path and report what is still missing.
#
#   ./install.sh
#
# Everything it does happens under $HOME. It never uses sudo, never edits a file
# outside ~/.local, and never installs anything you did not ask for: the TeX and
# Tailscale steps are printed for you to run, not run for you.
# ---------------------------------------------------------------------------
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="${XDG_BIN_HOME:-$HOME/.local/bin}"
ok=0

say()  { printf '%s\n' "$*"; }
good() { printf '  ok    %s\n' "$*"; }
warn() { printf '  ----  %s\n' "$*"; ok=1; }

say "Tutor-Board"
say "  $HERE"
say

# --- python ----------------------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  v="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
  case "$v" in
    3.[0-6]) warn "python3 is $v; 3.7 or newer is needed" ;;
    *)       good "python3 $v" ;;
  esac
else
  warn "no python3 on the path"
fi

# --- the launcher ----------------------------------------------------------
# A clone can arrive without the executable bit -- some filesystems and some
# archive paths drop it -- and then `board` is unrunnable for no visible reason.
# Put it back rather than making anyone diagnose it.
chmod +x "$HERE/bin/board" "$HERE/bin/tutor" "$HERE/serve.py" "$HERE/install.sh" \
        "$HERE/scripts/save-and-push.sh" "$HERE"/../.githooks/* 2>/dev/null || true
mkdir -p "$BIN"
ln -sf "$HERE/bin/board" "$BIN/board"
ln -sf "$HERE/bin/tutor" "$BIN/tutor"
good "tutor, board -> $BIN"
case ":$PATH:" in
  *":$BIN:"*) : ;;
  *) warn "$BIN is not on your PATH — add it to your shell profile" ;;
esac

# --- the daily pull --------------------------------------------------------
# `tutor resume` moves colibri and the Tailscale client forward on login, which
# is all a compute node needs. A workstation left up for a week never has one,
# so the same routine gets a timer. A --user timer because pam refuses crontab
# on this cluster.
#
# The wrapper is LINKED, so editing it here is what runs tomorrow. The units are
# COPIED: systemd reads the unit directory at daemon-reload, and a link into a
# repository that later moves is a timer that silently stops firing.
chmod +x "$HERE/scripts/tutor-pull" 2>/dev/null || true
ln -sf "$HERE/scripts/tutor-pull" "$BIN/tutor-pull"
if command -v systemctl >/dev/null 2>&1; then
  UNITS="$HOME/.config/systemd/user"
  mkdir -p "$UNITS" 2>/dev/null
  changed=0
  for unit in "$HERE"/scripts/systemd/*.timer "$HERE"/scripts/systemd/*.service; do
    [ -f "$unit" ] || continue
    cmp -s "$unit" "$UNITS/$(basename "$unit")" || {
      cp "$unit" "$UNITS/$(basename "$unit")" && changed=1
    }
  done
  if [ "$changed" -eq 1 ]; then
    systemctl --user daemon-reload 2>/dev/null
    systemctl --user enable --now tutor-pull.timer >/dev/null 2>&1
  fi
  if systemctl --user is-enabled tutor-pull.timer >/dev/null 2>&1; then
    good "tutor-pull.timer (colibri and tailscale, daily)"
    # THE OLD NAME FOR THIS EXACT JOB. It ran `tutor pull` too, so leaving both
    # enabled is the same work twice a day under two names, and the one nobody
    # can find is the one that keeps running.
    if systemctl --user is-enabled colibri-pull.timer >/dev/null 2>&1; then
      systemctl --user disable --now colibri-pull.timer >/dev/null 2>&1 \
        && say "        (disabled colibri-pull.timer, which is this under its old name)"
    fi
  else
    warn "tutor-pull.timer is not enabled; a machine left up will not pull"
    say  "        systemctl --user enable --now tutor-pull.timer"
  fi
elif command -v launchctl >/dev/null 2>&1; then
  # A MAC, which is a machine that comes back. launchd runs two agents:
  # tutor-pull.plist for the timer (every twenty seconds, `tutor pull --hear`
  # deciding whether a pull is due), and tutor-watch.plist for `tutor watch`,
  # so a reboot brings every board back. LaunchAgents, COPIED for the reason the units are, and loaded in
  # the login session -- the Mac logs its owner in by itself, and the keychain
  # holding git's credential and the assistants' logins is open only there.
  AGENTS="$HOME/Library/LaunchAgents"
  DOMAIN="gui/$(id -u)"
  mkdir -p "$AGENTS" 2>/dev/null
  for plist in "$HERE"/scripts/launchd/*.plist; do
    [ -f "$plist" ] || continue
    name="$(basename "$plist" .plist)"
    label="tutor-board.$name"
    dst="$AGENTS/$label.plist"
    if ! cmp -s "$plist" "$dst"; then
      cp "$plist" "$dst"
      # A bootout returns before the job has gone, and a bootstrap into that
      # gap is refused -- so wait for it to be gone, for a few seconds.
      launchctl bootout "$DOMAIN/$label" >/dev/null 2>&1
      for _ in 1 2 3 4 5 6 7 8 9 10; do
        launchctl print "$DOMAIN/$label" >/dev/null 2>&1 || break
        sleep 1
      done
    fi
    launchctl print "$DOMAIN/$label" >/dev/null 2>&1 \
      || launchctl bootstrap "$DOMAIN" "$dst" >/dev/null 2>&1
    if launchctl print "$DOMAIN/$label" >/dev/null 2>&1; then
      good "$label (launchd, $AGENTS)"
    else
      warn "$label is not loaded"
      say  "        launchctl bootstrap $DOMAIN $dst"
    fi
  done
  if [ "$(defaults read /Library/Preferences/com.apple.loginwindow autoLoginUser 2>/dev/null)" != "$(id -un)" ]; then
    warn "automatic login is off; after a reboot the boards wait for somebody to log in"
    say  "        System Settings > Users & Groups > Automatically log in as $(id -un)"
  fi
else
  say  "  ----  no systemctl; the daily pull needs a login to happen"
fi

# --- TeX -------------------------------------------------------------------
# TinyTeX hides its binaries under an architecture-named directory. Ask Python,
# which already knows.
TEXPATH="$(python3 -c 'import sys,os; sys.path.insert(0, "'"$HERE"'"); from tutorboard import tex; print(os.pathsep.join(tex.tex_bin_dirs()))' 2>/dev/null)"
[ -n "$TEXPATH" ] && export PATH="$TEXPATH:$PATH"
missing=""
for exe in latex pdflatex dvisvgm latexmk; do
  command -v "$exe" >/dev/null 2>&1 || missing="$missing $exe"
done
if [ -z "$missing" ]; then
  good "latex, pdflatex, dvisvgm, latexmk"
else
  warn "missing:$missing"
  say  "        TeX is only needed to compile diagrams and to export a lesson."
  say  "        A small installation is enough:"
  say  "          https://yihui.org/tinytex/   then:"
  say  "          tlmgr install dvisvgm standalone varwidth preview needspace"
  say  "        It installs under \$HOME, which is the only place a cluster node"
  say  "        lets you put anything. On a Mac: brew install texlive"
fi

# --- poppler: the papers' text, and reading a PDF on the board ---------------
if command -v pdftotext >/dev/null 2>&1 && command -v pdftoppm >/dev/null 2>&1; then
  good "pdftotext, pdftoppm (poppler)"
else
  warn "no poppler; a PDF cannot be read on the board — brew install poppler"
fi

for pkg in standalone varwidth preview needspace; do
  if kpsewhich "$pkg.sty" >/dev/null 2>&1; then
    good "$pkg.sty"
  else
    warn "$pkg.sty not found — tlmgr install $pkg"
  fi
done

# --- vendored KaTeX --------------------------------------------------------
if [ -f "$HERE/web/katex/katex.min.js" ]; then
  good "KaTeX vendored"
else
  warn "web/katex is empty — the repository is incomplete"
fi

# --- node, tests only ------------------------------------------------------
if command -v node >/dev/null 2>&1; then
  good "node $(node -v) (tests)"
else
  warn "no node; the test suite will not run, the board will"
fi

# --- tailscale, optional ---------------------------------------------------
ts_kind="$(python3 -c 'import sys; sys.path.insert(0, "'"$HERE"'"); from tutorboard.net import tailscale; print(tailscale.tailscale_cli()[1])' 2>/dev/null)"
case "$ts_kind" in
  system)
    good "tailscale (managed by this system — nothing for the board to start)" ;;
  userspace)
    good "tailscale (userspace daemon in \$HOME)" ;;
  *)
    say  "  ----  tailscale not installed (optional)"
    say  "        Only needed to reach the board from a device on another network."
    python3 -c 'import sys; sys.path.insert(0, "'"$HERE"'"); from tutorboard.net import tailscale; print(tailscale.tailscale_download_hint())' 2>/dev/null \
      | sed 's/^/          /'
    say  "        then: board vpn up" ;;
esac

say
if [ "$ok" -eq 0 ]; then
  say "Ready. From anywhere:"
else
  say "Usable, with the gaps above. From anywhere:"
fi
say "  tutor              # pick a course and begin"
say "  tutor --list       # what it can see"
say "  tutor --agents     # which assistants are configured"
exit 0
