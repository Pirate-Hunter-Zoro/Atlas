#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup.sh -- bring this repository to the point where `lake build` works,
# on whatever machine you happen to be sitting at.
#
#   ./scripts/setup.sh              install what is missing, then get Mathlib
#   ./scripts/setup.sh --check      report only; change nothing
#   ./scripts/setup.sh --source     skip the cache; build Mathlib from source
#
# Two machines are in play and they fail in different places, so nothing here
# is guessed at:
#
#   * a personal Mac -- nothing installed, but the network is open, so the
#     prebuilt Mathlib cache downloads in minutes and no compilation happens.
#
#   * a Laureate compute node -- elan already at ~/.elan, but egress filtering
#     lets the TCP connection to lakecache.blob.core.windows.net open and then
#     drops the TLS handshake. `lake exe cache get` therefore HANGS rather than
#     failing: eighteen minutes, zero artifacts, looking exactly like a slow
#     download. That is why the cache step below runs under a timeout and why a
#     timeout is treated as "this node cannot reach the cache", not as an error.
#     There, Mathlib is compiled from source instead -- hours on a laptop, tens
#     of minutes on 92 cores, and that is what slurm_jobs/build_mathlib.sbatch
#     is for.
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
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done

say()  { printf '%s\n' "$*"; }
good() { printf '  ok    %s\n' "$*"; }
warn() { printf '  ----  %s\n' "$*"; }
step() { printf '\n%s\n' "$*"; }

# How long to let the cache download sit before calling it blocked. A real
# download of a full Mathlib cache is minutes; the blocked handshake is
# forever. Ten minutes tells them apart without cutting a slow-but-working
# transfer short.
CACHE_TIMEOUT="${LEANTP_CACHE_TIMEOUT:-600}"

# `timeout` is coreutils and is not on a stock macOS, so do it in bash. A
# process killed this way comes back as 124, matching coreutils' convention.
run_capped() {
  local secs="$1"; shift
  "$@" & local pid=$!
  ( sleep "$secs"; kill -TERM "$pid" 2>/dev/null
    sleep 10;      kill -KILL "$pid" 2>/dev/null ) & local watcher=$!
  wait "$pid"; local rc=$?
  kill -TERM "$watcher" 2>/dev/null; wait "$watcher" 2>/dev/null
  # 143 = SIGTERM, which here means the watcher fired rather than a real failure.
  [ "$rc" -eq 143 ] && rc=124
  return $rc
}

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
  if [ -d "$ROOT/.lake/packages/mathlib" ]; then
    good "mathlib source present ($(du -sh "$ROOT/.lake" 2>/dev/null | awk '{print $1}') in .lake)"
    olean=$(find "$ROOT/.lake/packages/mathlib/.lake/build/lib" -name '*.olean' 2>/dev/null | head -1)
    [ -n "$olean" ] && good "mathlib is built" || warn "mathlib source is here but NOT built"
  else
    warn "mathlib has not been fetched"
  fi
  step "status"
  bash "$ROOT/scripts/status.sh" 2>/dev/null | tail -1
  exit 0
fi

# --- Mathlib ---------------------------------------------------------------
# Never compile this if you do not have to. Mathlib's CI publishes prebuilt
# .olean artifacts and `lake exe cache get` turns hours of compilation into a
# few minutes of transfer -- where the network allows it.
step "Mathlib"
if [ "$FORCE_SOURCE" = 1 ]; then
  say "  --source given; skipping the cache"
  CACHE_OK=1
else
  # Mathlib's git history is well over a gigabyte and the first call here has to
  # clone it. That transfer really does drop -- it did on this Mac, at "8005
  # bytes of body are still expected", after several minutes of successful
  # download -- and a half-written clone is not a reason to spend hours
  # compiling. So: retry a failure, but never retry a TIMEOUT, because a timeout
  # is the signature of a node that cannot reach the cache at all and retrying
  # it just spends another ten minutes proving the same thing.
  #
  # git's defaults give up on a stalled read sooner than a big clone deserves;
  # these three settings are set for this repository only, not globally.
  git config http.postBuffer 524288000    2>/dev/null || true
  git config http.lowSpeedLimit 1000      2>/dev/null || true
  git config http.lowSpeedTime 300        2>/dev/null || true

  CACHE_OK=1
  for attempt in 1 2 3; do
    say "  trying the prebuilt cache (attempt $attempt, capped at ${CACHE_TIMEOUT}s)"
    run_capped "$CACHE_TIMEOUT" lake exe cache get
    CACHE_OK=$?
    [ "$CACHE_OK" -eq 0 ] && break
    if [ "$CACHE_OK" -eq 124 ]; then
      warn "the cache did not answer within ${CACHE_TIMEOUT}s"
      warn "this node cannot reach lakecache.blob.core.windows.net —"
      warn "the TCP connect succeeds and the TLS handshake is dropped, so it"
      warn "hangs instead of failing. Building from source instead."
      warn "confirm with: curl -sv https://lakecache.blob.core.windows.net/"
      break
    fi
    warn "cache fetch failed (exit $CACHE_OK)"
    # A clone that died halfway cannot be resumed; lake will not retry it
    # either, it will just report the same broken checkout. Clear it.
    if [ -d "$ROOT/.lake/packages/mathlib" ] && \
       ! [ -d "$ROOT/.lake/packages/mathlib/.git" ]; then
      say "  clearing the incomplete mathlib checkout"
      rm -rf "$ROOT/.lake/packages/mathlib"
    fi
    [ "$attempt" -lt 3 ] && { say "  retrying in 15s"; sleep 15; }
  done
  [ "$CACHE_OK" -eq 0 ] && good "cache fetched"
  [ "$CACHE_OK" -ne 0 ] && [ "$CACHE_OK" -ne 124 ] && \
    warn "the cache could not be fetched after 3 attempts; building from source"
fi

step "build"
if [ "$CACHE_OK" = 0 ]; then
  say "  building the package against the cached Mathlib"
  lake build 2>&1 | grep -E "^(error|warning):" | grep -v "declaration uses 'sorry'" | head -20
  rc=${PIPESTATUS[0]}
elif [ "$ON_CLUSTER" = 1 ]; then
  say "  Mathlib must be compiled from source, and this is a cluster node."
  say "  Do not compile it on the login shell. Submit the job instead:"
  say
  say "      sbatch slurm_jobs/build_mathlib.sbatch"
  say
  say "  Progress lands in slurm_jobs/build_mathlib_out.txt, which is TRUNCATED"
  say "  on every submission — copy a run aside if it is worth keeping. The"
  say "  build is incremental, so resubmitting resumes rather than restarting."
  exit 0
else
  say "  compiling Mathlib from source. This is hours, not minutes, and it is"
  say "  a one-time cost — the artifacts land in .lake/ and persist until"
  say "  Mathlib or the toolchain is bumped."
  lake build 2>&1 | grep -E "^(error|warning):" | grep -v "declaration uses 'sorry'" | head -20
  rc=${PIPESTATUS[0]}
fi

step "status"
if [ "${rc:-1}" -eq 0 ]; then
  good "lake build succeeded"
else
  warn "lake build failed (exit ${rc:-?}) — run scripts/build.sh for the detail"
fi
bash "$ROOT/scripts/status.sh"
exit "${rc:-1}"
