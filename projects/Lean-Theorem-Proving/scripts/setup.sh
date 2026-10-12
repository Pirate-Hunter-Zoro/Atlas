#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup.sh -- bring this repository to the point where `lake build` works,
# on whatever machine you happen to be sitting at.
#
#   ./scripts/setup.sh              install what is missing, then start Mathlib
#   ./scripts/setup.sh --check      report only; change nothing
#   ./scripts/setup.sh --source     skip the cache; compile Mathlib from source
#
# It installs elan and the pinned toolchain, then hands Mathlib to
# scripts/build-mathlib.sh, which builds it in the background and returns at
# once. The exercises are built here only when Mathlib already is.
#
# Under Slurm it builds nothing. The cluster's egress filtering opens the TCP
# connection to lakecache.blob.core.windows.net and drops the TLS handshake, so
# `lake exe cache get` hangs rather than fails, and Mathlib is compiled by
# slurm_jobs/build_mathlib.sbatch instead.
#
# Everything happens under $HOME. No sudo, ever.
# ---------------------------------------------------------------------------
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

CHECK=0; FORCE_SOURCE=0
for a in "$@"; do
  case "$a" in
    --check)  CHECK=1 ;;
    --source) FORCE_SOURCE=1 ;;
    -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done

say()  { printf '%s\n' "$*"; }
good() { printf '  ok    %s\n' "$*"; }
warn() { printf '  ----  %s\n' "$*"; }
step() { printf '\n%s\n' "$*"; }

say "Lean-Theorem-Proving setup"
say "  $ROOT"
uname_s="$(uname -s)"; uname_m="$(uname -m)"
say "  $uname_s $uname_m"
if command -v sbatch >/dev/null 2>&1; then
  say "  Slurm is present — this looks like a cluster node"
  ON_CLUSTER=1
else
  ON_CLUSTER=0
fi

# --- elan ------------------------------------------------------------------
# Lean's version manager, the equivalent of rustup. It picks the compiler per
# project by reading lean-toolchain, so it is the only thing that has to be
# installed by hand.
step "elan"
export PATH="$HOME/.elan/bin:$PATH"
if command -v elan >/dev/null 2>&1; then
  good "elan $(elan --version 2>/dev/null | awk '{print $2}')"
elif [ "$CHECK" = 1 ]; then
  warn "elan is not installed"
else
  say "  installing elan into ~/.elan (no sudo, nothing outside \$HOME)"
  tmp="$(mktemp -d)"
  if curl -sSfL https://elan.lean-lang.org/elan-init.sh -o "$tmp/elan-init.sh"; then
    # --default-toolchain none: the toolchain this project wants is pinned in
    # lean-toolchain and installed in the next step. Do not fetch a second one.
    sh "$tmp/elan-init.sh" -y --default-toolchain none >/dev/null 2>&1
  fi
  rm -rf "$tmp"
  export PATH="$HOME/.elan/bin:$PATH"
  command -v elan >/dev/null 2>&1 && good "elan installed" || { warn "elan install failed"; exit 1; }
fi

case ":$PATH:" in
  *":$HOME/.elan/bin:"*) : ;;
  *) warn "~/.elan/bin is not on your PATH — add it to your shell profile" ;;
esac

# --- the pinned toolchain --------------------------------------------------
# Not chosen: copied from Mathlib's own lean-toolchain. Mathlib's compiled
# artifacts are only valid for the exact Lean version they were built against,
# so this file tracks Mathlib's pin and never the other way round.
step "toolchain"
TOOLCHAIN="$(tr -d '[:space:]' < "$ROOT/lean-toolchain")"
if elan toolchain list 2>/dev/null | grep -q "^${TOOLCHAIN}"; then
  good "$TOOLCHAIN already installed"
elif [ "$CHECK" = 1 ]; then
  warn "$TOOLCHAIN is not installed"
else
  say "  installing $TOOLCHAIN"
  elan toolchain install "$TOOLCHAIN" >/dev/null 2>&1 \
    && good "$TOOLCHAIN" || { warn "could not install $TOOLCHAIN"; exit 1; }
fi
command -v lean >/dev/null 2>&1 && good "$(lean --version)"

if [ "$CHECK" = 1 ]; then
  step "Mathlib"
  said="$(bash "$ROOT/scripts/build-mathlib.sh" --status)"
  [ $? -eq 0 ] && good "$said" || warn "$said"
  step "status"
  bash "$ROOT/scripts/status.sh" 2>/dev/null | tail -1
  exit 0
fi

# --- Mathlib ---------------------------------------------------------------
step "Mathlib"
if [ "$ON_CLUSTER" = 1 ]; then
  said="$(bash "$ROOT/scripts/build-mathlib.sh" --status)"
  if [ $? -eq 0 ]; then
    good "Mathlib is $said"
  else
    say "  Mathlib is $said, and this is a cluster node. Do not compile it on"
    say "  the login shell. Submit the job instead:"
    say
    say "      sbatch slurm_jobs/build_mathlib.sbatch"
    say
    say "  Progress lands in slurm_jobs/build_mathlib_out.txt, which is TRUNCATED"
    say "  on every submission. The build is incremental, so resubmitting resumes."
  fi
  exit 0
fi
source_arg=()
[ "$FORCE_SOURCE" = 1 ] && source_arg=(--source)
said="$(bash "$ROOT/scripts/build-mathlib.sh" ${source_arg[@]+"${source_arg[@]}"} 2>&1)" \
  || { warn "$said"; exit 1; }
good "Mathlib $said"

step "build"
if ! bash "$ROOT/scripts/build-mathlib.sh" --status >/dev/null; then
  say "  the exercises build once Mathlib has: scripts/build-mathlib.sh --status"
  bash "$ROOT/scripts/status.sh" | tail -1
  exit 0
fi
lake build 2>&1 | grep -E "^(error|warning):" | grep -Ev "declaration uses [\`']sorry[\`']" | head -20
rc=${PIPESTATUS[0]}

step "status"
if [ "${rc:-1}" -eq 0 ]; then
  good "lake build succeeded"
else
  warn "lake build failed (exit ${rc:-?}) — run scripts/build.sh for the detail"
fi
bash "$ROOT/scripts/status.sh"
exit "${rc:-1}"
