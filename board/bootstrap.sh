#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# bootstrap.sh -- set a new machine up as a tutoring host.
#
#   bash board/bootstrap.sh [--name <tailnet-name>] [--no-clone]
#
# Run it once on the machine that will run the board: a cluster node, a desktop,
# a laptop. It puts `tutor` and `board` on the path, fills in the vendored
# submodules, reports what is missing, and tells you what remains.
#
# It does not use sudo, does not install anything system-wide, and does not
# start anything you did not ask for.
#
# IT NO LONGER CLONES ANYTHING, and that is the whole of what the move to one
# repository did to this file. It used to read a private list of eleven git URLs
# from ~/.config/tutor-board/courses.txt and clone each of them beside the tool
# -- a list kept out of this repository because this repository is public, and a
# list that therefore had to be copied by hand onto every new machine and kept in
# step with reality for ever.
#
# There is one repository now. Setting a machine up is:
#
#     git clone --recurse-submodules https://github.com/Pirate-Hunter-Zoro/Atlas.git
#     bash Atlas/board/bootstrap.sh
#
# and everything arrives together, at the same commit, with nothing to remember.
# What is left here is the vendored submodules -- `--recurse-submodules` is the
# first thing a new machine gets wrong -- and `--no-clone` still skips that.
# ---------------------------------------------------------------------------
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The repository root -- the directory holding atlas.json, one level above the
# tool. It was the tool's parent because the courses were its siblings, which is
# the same sentence about a different shape.
ROOT="$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null || dirname "$HERE")"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/tutor-board"
NAME=""
CLONE=1

while [ $# -gt 0 ]; do
  case "$1" in
    --name)    shift; NAME="$1" ;;
    --no-clone) CLONE=0 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown option: $1"; exit 1 ;;
  esac
  shift
done

say()  { printf '%s\n' "$*"; }
good() { printf '  ok    %s\n' "$*"; }
warn() { printf '  ----  %s\n' "$*"; }

say "Atlas bootstrap"
say "  repository: $ROOT"
say "  the board:  $HERE"
say

# --- the tool itself --------------------------------------------------------
bash "$HERE/install.sh" | sed 's/^/  /'
say

# --- the vendored submodules ------------------------------------------------
# Somebody else's repositories, tracked by pointer. A clone made without
# `--recurse-submodules` arrives with an EMPTY vendor/, which is the first thing
# a new machine gets wrong and gives no error when it happens -- the directory is
# simply there and has nothing in it.
if [ "$CLONE" -eq 1 ]; then
  if [ -f "$ROOT/.gitmodules" ]; then
    say "Filling in the vendored submodules"
    if git -C "$ROOT" submodule update --init --recursive >/dev/null 2>&1; then
      while read -r _ path _; do
        [ -n "$path" ] || continue
        if [ -n "$(ls -A "$ROOT/$path" 2>/dev/null)" ]; then
          good "$path at $(git -C "$ROOT/$path" rev-parse --short HEAD 2>/dev/null)"
        else
          warn "$path is still empty"
        fi
      done < <(git -C "$ROOT" submodule status | awk '{print $1, $2, $3}')
    else
      warn "could not fetch the submodules; vendor/ will be empty until there is a network"
      say  "        git -C $ROOT submodule update --init --recursive"
    fi
  else
    warn "no .gitmodules at $ROOT -- is the board inside its repository?"
  fi
  say
fi

# --- tailnet identity -------------------------------------------------------
if [ -n "$NAME" ]; then
  export BOARD_TAILNET_NAME="$NAME"
  # Refuse to rename a machine that already answers to something on the tailnet,
  # unless that is plainly what was meant. Renaming a live node moves the address
  # every installed app points at.
  EXISTING="$(python3 -c "
import sys; sys.path.insert(0, '$HERE')
import boardlib, os
print(boardlib.tailnet_hostname() if os.path.exists(boardlib.TS_NAME_FILE) else '')
" 2>/dev/null)"
  if [ -n "$EXISTING" ] && [ "$EXISTING" != "$NAME" ]; then
    warn "this machine already calls itself '$EXISTING' on the tailnet"
    say  "        Renaming it to '$NAME' would move the address any installed app"
    say  "        points at. If that is what you want:"
    say  "          board vpn up --hostname $NAME"
    NAME=""
  fi
fi

if [ -n "$NAME" ]; then
  python3 -c "
import sys; sys.path.insert(0, '$HERE')
import boardlib; boardlib.set_tailnet_hostname('$NAME')
print('  ok    this machine will call itself \'$NAME\' on the tailnet')
"
else
  say "  ----  no --name given; this machine will call itself 'board'"
  say "        Two hosts cannot both be 'board'. If another machine already"
  say "        holds that name, re-run with --name <something-else>."
fi
say

# --- what is left -----------------------------------------------------------
say "Next:"
say "  board vpn up          link this machine to your tailnet (prints a login URL once)"
say "  board vpn serve       HTTPS on its *.ts.net name, so the iPad app works offline"
say "  tutor --list          confirm it can see the courses"
say "  tutor --agents        point it at the assistant you use here"
say "  tutor galois          start a session"
say
say "  tutor headless galois --agent opencode     run it as a daemon"
say "  bash $HERE/scripts/install-autostart.sh --login-hook"
say "                                            and it comes back by itself on"
say "                                            every node you are given"
