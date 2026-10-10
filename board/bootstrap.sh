#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# bootstrap.sh -- set a new machine up as a tutoring host.
#
#   bash board/bootstrap.sh [--name <tailnet-name>] [--no-clone]
#   bash board/bootstrap.sh --private-only
#
# Run it once on each machine: the Mac, which runs the board, and the cluster,
# which runs only the relay. It puts `board` on the path, fills in the vendored
# submodules, brings in ai-config, reports what is missing, and
# tells you what remains. Run it again whenever you are not sure: every step is
# idempotent.
#
# It does not use sudo, does not install anything system-wide, and does not
# start anything you did not ask for.
#
# Setting a machine up is:
#
#     git clone --recurse-submodules https://github.com/Pirate-Hunter-Zoro/Atlas.git
#     bash Atlas/board/bootstrap.sh
#
# Atlas is public and arrives with its vendored submodules and every course and
# project. ai-config, the one private repository nested inside it and ignored
# by it, cannot arrive with it, so this clones it from AI_CONFIG_URL with the
# owner's credentials (git, then `gh repo clone`). An ai-config directory that
# is already there with files in it and no .git is ADOPTED in place: its
# history is fetched underneath the files, nothing on disk is overwritten, a
# file missing from disk is restored, and local edits stay as uncommitted
# changes. Then it gets the commit-msg hook: its own .githooks/ if it carries
# one, Atlas's by absolute path if not.
#
# Atlas itself gets core.hooksPath set to its .githooks/ by ABSOLUTE path, so
# every worktree runs the same commit-msg and pre-commit hooks.
#
# `--no-clone` skips the submodules and the cloning; hooks are still set on
# Atlas and on ai-config if it is already there.
# `--private-only` runs the hook and ai-config steps and nothing else --
# the board server's cluster thread (`gitops.adopt_private`) calls it, so there
# is one copy of that logic.
# ---------------------------------------------------------------------------
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The repository root, one level above the tool.
ROOT="$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null || dirname "$HERE")"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/tutor-board"
NAME=""
CLONE=1
PRIVATE_ONLY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --name)    shift; NAME="$1" ;;
    --no-clone) CLONE=0 ;;
    --private-only) PRIVATE_ONLY=1 ;;
    -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
    *) echo "unknown option: $1"; exit 1 ;;
  esac
  shift
done

say()  { printf '%s\n' "$*"; }
good() { printf '  ok    %s\n' "$*"; }
warn() { printf '  ----  %s\n' "$*"; }

# --- ai-config ---------------------------------------------------------------
# The one private repository nested inside Atlas. Its URL is fixed here and in
# tutorboard/gitops.py's AI_CONFIG_URL; nothing else is ever cloned into the tree.
AI_CONFIG="ai-config"
AI_CONFIG_URL="https://github.com/Pirate-Hunter-Zoro/ai-config.git"

# Fetch ai-config's history underneath files already on disk.
# Every step is non-destructive and safe to repeat: a mixed reset moves the
# index and HEAD and never the working tree, so a local edit shows as a
# modification, and only files MISSING from disk are checked out. No git
# command here may prompt: the periodic pull runs this with nobody at the terminal,
# and a username prompt there is a job that hangs until its allocation ends.
adopt() {
  local dest="$1" url="$2"
  git -C "$dest" init -q -b main >/dev/null 2>&1 || git -C "$dest" init -q || return 1
  git -C "$dest" remote add origin "$url" 2>/dev/null \
    || git -C "$dest" remote set-url origin "$url" || return 1
  GIT_TERMINAL_PROMPT=0 git -C "$dest" fetch -q origin || return 1
  git -C "$dest" reset -q origin/main || return 1
  git -C "$dest" branch -q --set-upstream-to origin/main >/dev/null 2>&1
  if [ -n "$(git -C "$dest" ls-files -d)" ]; then
    git -C "$dest" ls-files -d -z | xargs -0 git -C "$dest" checkout -- || return 1
  fi
}

ai_config() {
  local path="$AI_CONFIG" url="$AI_CONFIG_URL" dest gh_name hooks n
  dest="$ROOT/$path"
  say "The private repository"
  # A .git with no commit behind it is an adoption that stopped part-way;
  # adopt() is safe to run again over it.
  if [ "$CLONE" -eq 1 ] && { [ ! -e "$dest/.git" ] \
       || ! git -C "$dest" rev-parse -q --verify HEAD >/dev/null 2>&1; }; then
    if [ ! -d "$dest" ] || [ -z "$(ls -A "$dest" 2>/dev/null)" ]; then
      gh_name="${url#https://github.com/}"; gh_name="${gh_name%.git}"
      if GIT_TERMINAL_PROMPT=0 git clone -q "$url" "$dest" >/dev/null 2>&1 \
         || { command -v gh >/dev/null 2>&1 \
              && gh repo clone "$gh_name" "$dest" -- -q >/dev/null 2>&1; }; then
        good "$path: cloned"
      else
        warn "$path: could not clone (private: it needs the owner's credentials)"
        say  "        gh auth login && gh repo clone $gh_name $dest"
        say; return 0
      fi
    elif ! adopt "$dest" "$url" >/dev/null 2>&1; then
      warn "$path: has files but no history, and adopting it from $url stopped"
      say  "        no file on disk was overwritten; re-run once 'gh auth login' works"
      say; return 0
    else
      n="$(git -C "$dest" status --porcelain | grep -c . || true)"
      good "$path: adopted in place; ${n:-0} local change(s) kept, uncommitted"
    fi
  elif [ -e "$dest/.git" ] && git -C "$dest" rev-parse -q --verify HEAD >/dev/null 2>&1; then
    good "$path: already a repository"
  else
    warn "$path: not cloned or adopted (--no-clone)"
    say; return 0
  fi
  # The commit-msg hook, on from the first commit -- including the ones that
  # never go through save-and-push.sh. Relative only where the repository
  # carries its own copy; a relative path anywhere else finds nothing.
  if [ -d "$dest/.githooks" ]; then hooks=".githooks"; else hooks="$ROOT/.githooks"; fi
  git -C "$dest" config core.hooksPath "$hooks"
  git -C "$dest" config core.fileMode false
  say
}

# Atlas's own hooks: commit-msg strips attribution, pre-commit is the
# commit-time gate (board/tutorboard/audit.py). Absolute, so a worktree finds
# them too.
atlas_hooks() {
  if [ -d "$ROOT/.githooks" ]; then
    chmod +x "$ROOT"/.githooks/* 2>/dev/null || true
    git -C "$ROOT" config core.hooksPath "$ROOT/.githooks"
    good "Atlas hooks: core.hooksPath = $ROOT/.githooks"
  else
    warn "no .githooks at $ROOT; commits here run no hooks"
  fi
}

if [ "$PRIVATE_ONLY" -eq 1 ]; then
  atlas_hooks
  ai_config
  exit 0
fi

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

say "The commit hooks"
atlas_hooks
say

ai_config

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
say "  tailscale serve --bg --https=443 http://127.0.0.1:8778   publish the board once (the Mac)"
say "  board vpn             what tailscale says, and where HTTPS points"
say "  board doctor --dry    what this machine has, without spending a turn"
say
say "  bash $ROOT/scripts/setup-cluster.sh   on the cluster: everything, from a compute node"
