#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# install.sh -- put `board` on the path, install the one LaunchAgent, and
# report what is still missing.
#
#   ./install.sh
#   ./install.sh --plist [ARG...]   print the LaunchAgent, installing nothing
#
# Everything it does happens under $HOME. It never uses sudo, never edits a file
# outside ~/.local and ~/Library/LaunchAgents, and never installs anything you
# did not ask for: the TeX and Tailscale steps are printed for you to run, not
# run for you.
#
# `--plist` fills scripts/launchd/tutor-board.plist and prints it: ARGs are
# appended to serve.py's, TUTORBOARD_LABEL renames the job, TUTORBOARD_LOG
# moves its log, and PYTHON names the interpreter. A rehearsal renders a test
# job with it; nothing else should.
# ---------------------------------------------------------------------------
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="${XDG_BIN_HOME:-$HOME/.local/bin}"
ok=0

# The PATH the LaunchAgent runs with. Its interpreter is the first python3 on
# it, so the server and every `board` its turns run are the same Python.
AGENT_PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
STATE="$HOME/.local/state/tutor-board"

agent_python() {
  if [ -n "${PYTHON:-}" ]; then
    printf '%s\n' "$PYTHON"
    return
  fi
  PATH="$AGENT_PATH" command -v python3
}

# render_plist [ARG...]: the LaunchAgent on stdout, every path absolute.
render_plist() {
  local py
  py="$(agent_python)"
  case "$py" in
    /*) : ;;
    *) echo "install.sh: no python3 on $AGENT_PATH (set PYTHON)" >&2; return 1 ;;
  esac
  "$py" - "$HERE/scripts/launchd/tutor-board.plist" "$py" "$HERE" \
      "$(dirname "$HERE")" "$HOME" "${TUTORBOARD_LOG:-$STATE/server.log}" \
      "${TUTORBOARD_LABEL:-tutor-board}" "$@" <<'PYEOF'
import plistlib, sys
src, py, board, atlas, home, log, label = sys.argv[1:8]
extra = sys.argv[8:]
with open(src, "rb") as fh:
    job = plistlib.load(fh)
fill = {"@PYTHON@": py, "@BOARD@": board, "@ATLAS@": atlas, "@HOME@": home,
        "@LOG@": log}
def sub(v):
    if isinstance(v, str):
        for k, w in fill.items():
            v = v.replace(k, w)
        return v
    if isinstance(v, list):
        return [sub(x) for x in v]
    if isinstance(v, dict):
        return dict((k, sub(x)) for k, x in v.items())
    return v
job = sub(job)
job["Label"] = label
job["ProgramArguments"] += extra
sys.stdout.write(plistlib.dumps(job).decode("utf-8"))
PYEOF
}

if [ "${1:-}" = "--plist" ]; then
  shift
  render_plist "$@"
  exit $?
fi

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

# --- the Mac's one agent ----------------------------------------------------
# A Mac runs the board; nothing else does. launchd runs one agent there,
# `tutor-board`: board/serve.py, kept alive, which pulls and hears the cluster
# itself and exits for a restart when committed board code changes. The
# cluster's only schedule is the relay's scrontab entry (`scripts/setup-cluster.sh`).
#
# The agent is RENDERED and COPIED: launchd reads it at bootstrap and expands
# nothing, so every path in it is absolute, the interpreter included.
if command -v launchctl >/dev/null 2>&1; then
  AGENTS="$HOME/Library/LaunchAgents"
  DOMAIN="gui/$(id -u)"
  LABEL="tutor-board"
  mkdir -p "$AGENTS" "$STATE" 2>/dev/null
  # The agents this one replaces: the 20-second pull timer and the watchdog
  # that kept one board per workspace up.
  for old in tutor-board.tutor-pull tutor-board.tutor-watch; do
    if launchctl print "$DOMAIN/$old" >/dev/null 2>&1; then
      launchctl bootout "$DOMAIN/$old" >/dev/null 2>&1
      good "booted out $old"
    fi
    rm -f "$AGENTS/$old.plist"
  done
  rm -f "$BIN/tutor-pull"
  dst="$AGENTS/$LABEL.plist"
  new="$(mktemp "${TMPDIR:-/tmp}/tutor-board.XXXXXX")"
  if ! render_plist > "$new" || ! plutil -lint "$new" >/dev/null 2>&1; then
    warn "$LABEL could not be rendered; nothing installed"
  else
    if ! cmp -s "$new" "$dst"; then
      cp "$new" "$dst"
      # A bootout returns before the job has gone, and a bootstrap into that
      # gap is refused -- so wait for it to be gone, for a few seconds.
      launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1
      for _ in 1 2 3 4 5 6 7 8 9 10; do
        launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1 || break
        sleep 1
      done
    fi
    launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1 \
      || launchctl bootstrap "$DOMAIN" "$dst" >/dev/null 2>&1
    if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
      good "$LABEL (launchd, $dst; log $STATE/server.log)"
    else
      warn "$LABEL is not loaded"
      say  "        launchctl bootstrap $DOMAIN $dst"
    fi
  fi
  rm -f "$new"
  if [ "$(defaults read /Library/Preferences/com.apple.loginwindow autoLoginUser 2>/dev/null)" != "$(id -un)" ]; then
    warn "automatic login is off; after a reboot the board waits for somebody to log in"
    say  "        System Settings > Users & Groups > Automatically log in as $(id -un)"
  fi
else
  say  "  ----  no launchd: the board runs on the Mac, so nothing is scheduled here"
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
  say  "        TeX is only needed to compile diagrams and documents."
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
say "  tutor --list       # what it can see"
say "  tutor --agents     # which assistants are configured"
exit 0
