#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# build-mathlib.sh -- build this checkout's Mathlib in the background.
#
#   ./scripts/build-mathlib.sh            start: the prebuilt cache, then an
#                                         incremental `lake build Mathlib`
#   ./scripts/build-mathlib.sh --source   start without the cache: compile
#   ./scripts/build-mathlib.sh --status   report only; exit 0 built, 1 missing,
#                                         2 running, 3 failed
#
# Starting returns at once with one line: built, running or started. The build
# runs under nohup and `caffeinate -is`, so a closed terminal or an idle Mac
# does not stop it. Its lock, log and status file are in
# ~/.local/state/atlas-setup/, named for this checkout; the log of the run
# before is kept beside it as .prev.log.
#
# Built means Mathlib.olean exists, the mathlib checkout is at the commit
# lake-manifest.json pins, and the last build here did not fail. A checkout at
# any other commit counts as missing, because `lake build` would compile it
# in the foreground.
#
# LEAN_NUM_THREADS is the core count capped at 8, which keeps a source build
# inside 24 GB of RAM; LEANTP_THREADS overrides it. Under Slurm it will not
# start a build: slurm_jobs/build_mathlib.sbatch is the build there.
# ---------------------------------------------------------------------------
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SELF="$ROOT/scripts/build-mathlib.sh"
export PATH="$HOME/.elan/bin:$PATH"
cd "$ROOT" || exit 1

STATE="${XDG_STATE_HOME:-$HOME/.local/state}/atlas-setup"
name="${ROOT#"$HOME"/}"
name="mathlib-${name//\//_}"
LOCK="$STATE/$name.lock"      # a directory; each file in it holds a pid of the build
LOG="$STATE/$name.log"
PREV="$STATE/$name.prev.log"
STATUS="$STATE/$name.status"  # running, built or failed
MATHLIB="$ROOT/.lake/packages/mathlib"
OLEAN="$MATHLIB/.lake/build/lib/lean/Mathlib.olean"

SOURCE=0; MODE=start
for a in "$@"; do
  case "$a" in
    --source) SOURCE=1 ;;
    --status) MODE=status ;;
    --run)    MODE=run ;;   # the background half; started by this script only
    -h|--help) sed -n '2,25p' "$SELF"; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 64 ;;
  esac
done

# A pid counts only while its command line is still this script, so a pid
# reused after a reboot is not a build.
alive() {
  ps -p "$1" -o command= 2>/dev/null | grep -q 'build-mathlib\.sh'
}

# The pid of a live build, or nothing.
holder() {
  local f pid
  [ -d "$LOCK" ] || return 1
  for f in "$LOCK"/*; do
    pid="$(cat "$f" 2>/dev/null)"
    [ -n "$pid" ] || continue
    if alive "$pid"; then
      echo "$pid"; return 0
    fi
  done
  return 1
}

# The mathlib commit lake-manifest.json pins: "rev" comes before "name" in
# each package's entry.
pinned() {
  awk -F'"' '$2 == "rev" { rev = $4 } $2 == "name" && $4 == "mathlib" { print rev; exit }' \
    "$ROOT/lake-manifest.json" 2>/dev/null
}

status() {
  local pid last
  if pid="$(holder)"; then
    echo "running (pid $pid); log $LOG"; return 2
  fi
  last="$(cat "$STATUS" 2>/dev/null)"
  case "$last" in
    failed)  echo "failed; log $LOG"; return 3 ;;
    running) echo "failed: the build stopped without finishing; log $LOG"; return 3 ;;
  esac
  if [ ! -f "$OLEAN" ]; then
    echo "missing"; return 1
  fi
  if [ "$(git -C "$MATHLIB" rev-parse HEAD 2>/dev/null)" != "$(pinned)" ]; then
    echo "missing: the mathlib checkout is not at the commit lake-manifest.json pins"; return 1
  fi
  echo "built"; return 0
}

cores="$(sysctl -n hw.ncpu 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 8)"
[ "$cores" -gt 8 ] 2>/dev/null && cores=8
threads="${LEANTP_THREADS:-$cores}"

if [ "$MODE" = status ]; then
  status; exit $?
fi

if [ "$MODE" = start ]; then
  if command -v sbatch >/dev/null 2>&1; then
    echo "this is a Slurm cluster; Mathlib builds as a job: sbatch slurm_jobs/build_mathlib.sbatch" >&2
    exit 1
  fi
  case "$threads" in
    ''|*[!0-9]*|0) echo "LEANTP_THREADS must be a positive whole number, not '$threads'" >&2
                   exit 64 ;;
  esac
  mkdir -p "$STATE" || exit 1
  # Starts take turns, from the status check until the lock holds a pid: two at
  # once would each find no build, and each clear the lock the other had taken.
  # The turn is a symlink naming its start's pid, which ln makes or refuses in
  # one step; a turn whose start is dead is cleared.
  TURN="$STATE/$name.starting"
  took=0
  for _ in $(seq 100); do
    if ln -s "$$" "$TURN" 2>/dev/null; then took=1; break; fi
    other="$(readlink "$TURN" 2>/dev/null)"
    [ -n "$other" ] || continue
    if ! alive "$other"; then
      [ "$(readlink "$TURN" 2>/dev/null)" = "$other" ] && rm -f "$TURN"
      continue
    fi
    sleep 0.1
  done
  if [ "$took" = 0 ]; then
    echo "another start (pid $other) has held $TURN for 10s" >&2; exit 1
  fi
  trap '[ "$(readlink "$TURN" 2>/dev/null)" = "$$" ] && rm -f "$TURN"' EXIT
  said="$(status)"; rc=$?
  case "$rc" in
    0|2) echo "$said"; exit 0 ;;
  esac
  rm -rf "$LOCK"   # status() found no live holder, and no other start is past it
  if ! mkdir "$LOCK" 2>/dev/null; then
    echo "could not take the lock $LOCK" >&2; exit 1
  fi
  echo "$$" >"$LOCK/start"
  echo running >"$STATUS"
  [ -f "$LOG" ] && mv -f "$LOG" "$PREV"
  args=(--run)
  [ "$SOURCE" = 1 ] && args+=(--source)
  wrap=(nohup)
  command -v caffeinate >/dev/null 2>&1 && wrap+=(caffeinate -is)
  # Every descriptor is redirected, so a caller reading this script through a
  # pipe (setup-mac.sh's tee) is not held open for the hours a build takes.
  "${wrap[@]}" bash "$SELF" "${args[@]}" </dev/null >"$LOG" 2>&1 &
  # A build that fails at once may have removed the lock already.
  echo "$!" 2>/dev/null >"$LOCK/pid"
  rm -f "$LOCK/start"
  echo "started (pid $!$([ "$rc" = 3 ] && echo ", after a failed build: $PREV")); log $LOG"
  exit 0
fi

# ---- the background half -----------------------------------------------------
echo "$$" >"$LOCK/run"
child=""
finish() {
  echo "$1" >"$STATUS"
  rm -rf "$LOCK"
}
stopped() {
  [ -n "$child" ] && kill -TERM "$child" 2>/dev/null
  echo "stopped by a signal at $(date '+%F %T')"
  finish failed
  exit 143
}
trap stopped TERM INT

export LEAN_NUM_THREADS="$threads"

echo "started:   $(date '+%F %T')"
echo "checkout:  $ROOT"
echo "toolchain: $(cat lean-toolchain)"
echo "threads:   $LEAN_NUM_THREADS"
echo

# A command run in the background and waited on, so the TERM trap above fires
# while it runs rather than after it. Exit 124 means it hit the cap.
CACHE_TIMEOUT="${LEANTP_CACHE_TIMEOUT:-600}"
waited() {
  local secs="$1" watcher="" rc; shift
  "$@" & child=$!
  if [ "$secs" -gt 0 ]; then
    ( sleep "$secs"; kill -TERM "$child" 2>/dev/null
      sleep 10;      kill -KILL "$child" 2>/dev/null ) & watcher=$!
  fi
  wait "$child"; rc=$?
  child=""
  if [ -n "$watcher" ]; then
    kill -TERM "$watcher" 2>/dev/null; wait "$watcher" 2>/dev/null
    [ "$rc" -eq 143 ] && rc=124
  fi
  return "$rc"
}

if [ "$SOURCE" = 1 ]; then
  echo "--source: skipping the cache"
else
  # Mathlib's git history is over a gigabyte and the first fetch clones it; that
  # clone can drop mid-transfer. A failure is retried, after clearing a checkout
  # left without its .git. A timeout is not: it is a host that cannot reach the
  # cache at all, and the build below compiles instead. The git settings reach
  # lake's own clones through the environment and nowhere else.
  export GIT_CONFIG_COUNT=3 \
    GIT_CONFIG_KEY_0=http.postBuffer     GIT_CONFIG_VALUE_0=524288000 \
    GIT_CONFIG_KEY_1=http.lowSpeedLimit  GIT_CONFIG_VALUE_1=1000 \
    GIT_CONFIG_KEY_2=http.lowSpeedTime   GIT_CONFIG_VALUE_2=300
  for attempt in 1 2 3; do
    echo "lake exe cache get (attempt $attempt, capped at ${CACHE_TIMEOUT}s)"
    waited "$CACHE_TIMEOUT" lake exe cache get; rc=$?
    [ "$rc" -eq 0 ] && { echo "cache fetched"; break; }
    if [ "$rc" -eq 124 ]; then
      echo "the cache did not answer within ${CACHE_TIMEOUT}s; compiling instead"
      break
    fi
    echo "cache fetch failed (exit $rc)"
    if [ -d "$MATHLIB" ] && [ ! -e "$MATHLIB/.git" ]; then
      echo "clearing the incomplete mathlib checkout"
      rm -rf "$MATHLIB"
    fi
    [ "$attempt" -lt 3 ] && { echo "retrying in 15s"; sleep 15; }
  done
fi

echo
echo "lake build Mathlib"
waited 0 lake build Mathlib; rc=$?
echo
echo "finished:  $(date '+%F %T')"
echo "lake build exit status: $rc"
if [ "$rc" -eq 0 ] && [ -f "$OLEAN" ]; then
  finish built
else
  [ "$rc" -eq 0 ] && { echo "lake build exited 0 but $OLEAN is not there"; rc=1; }
  finish failed
fi
exit "$rc"
