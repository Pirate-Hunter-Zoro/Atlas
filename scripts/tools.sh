#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# tools.sh -- the tools neither brew nor mise keeps current, from descriptors.
#
#     bash scripts/tools.sh install          install each declared tool that is missing
#     bash scripts/tools.sh update [--force] update each one T_EVERY_DAYS after its last try
#     bash scripts/tools.sh list             each declared tool: where, version, subjects
#     bash scripts/tools.sh path             the directories they live in, colon-joined
#     bash scripts/tools.sh check            run each installed tool's T_CHECK
#
# A descriptor is <subject>/tools/<name>.sh, shaped like
# ai-config/assistants/<name>.sh: it sets these and nothing else.
#   T_NAME        the file's name without .sh
#   T_BIN         the command that proves it is installed
#   T_BIN_DIR     where T_INSTALL puts it when that is not on the PATH, or ""
#   T_ROLES       the roles it belongs on, "host", "coding" or both; "" is both
#   T_INSTALL     one command that installs it under $HOME with no prompt, or ""
#   T_MANUAL      what the owner does by hand when there is no T_INSTALL or it fails
#   T_UPDATE      one command that updates it in place, or "": then the owner
#                 updates it by T_MANUAL, and it is reported only as stale
#   T_VERSION     one command whose first line holds its version
#   T_CHECK       one command that exits 0 when it works, or ""
#   T_EVERY_DAYS  days between updates (1), less four hours
#   T_STALE_DAYS  days without a working update, or without a new version
#                 when there is no T_UPDATE, before it is reported (14)
#
# This file names no tool. One name declared in two subjects must be the same
# bytes; otherwise neither copy is used and the run fails. Results go to
# tools.json in the board's state directory (board/tutorboard/toolplan.py),
# which brewcare reports. Nothing is ever uninstalled: a tool whose descriptor
# is gone is reported as no longer declared. What each command printed is in
# ~/.local/state/atlas-setup/tools.log. Exit 1 when anything failed.
# ---------------------------------------------------------------------------
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="${XDG_STATE_HOME:-$HOME/.local/state}/atlas-setup"
LOG="$LOGS/tools.log"
mkdir -p "$LOGS"
ROLE=host
[ "$(tr -d '[:space:]' 2>/dev/null <"${XDG_CONFIG_HOME:-$HOME/.config}/tutor-board/role")" = coding ] \
  && ROLE=coding

# board/tutorboard/toolplan.py, from board/ so no other tutorboard is found first.
plan() {
  (cd "$ROOT/board" && python3 -B -m tutorboard.toolplan "$@" --atlas "$ROOT")
}

CMD="${1:-}"
FORCE=0
case "$CMD" in
  install|list|path|check) [ "$#" -eq 1 ] || { echo "usage: tools.sh $CMD" >&2; exit 2; } ;;
  update) case "${2:-}" in "") ;; --force) FORCE=1 ;; *) echo "usage: tools.sh update [--force]" >&2; exit 2 ;; esac ;;
  *) echo "usage: tools.sh install | update [--force] | list | path | check" >&2; exit 2 ;;
esac

FIELDS="T_NAME T_BIN T_BIN_DIR T_ROLES T_INSTALL T_MANUAL T_UPDATE T_VERSION T_CHECK T_EVERY_DAYS T_STALE_DAYS"

# One descriptor into this shell, the last one's fields cleared first.
load_tool() {
  # shellcheck disable=SC2086
  unset $FIELDS
  # shellcheck disable=SC1090
  . "$2" || return 1
  [ "${T_NAME:-}" = "$1" ] && [ -n "${T_BIN:-}" ]
}

# The PATH a tool's commands run with: its own directory first.
tool_path() {
  if [ -n "${T_BIN_DIR:-}" ]; then printf '%s:%s' "$T_BIN_DIR" "$PATH"; else printf '%s' "$PATH"; fi
}
found_bin() { PATH="$(tool_path)" command -v "$T_BIN" 2>/dev/null; }
run_tool() { (PATH="$(tool_path)"; export PATH; bash -c "$1") </dev/null >>"$LOG" 2>&1; }
version_of() {
  [ -n "${T_VERSION:-}" ] || return 0
  (PATH="$(tool_path)"; export PATH; bash -c "$T_VERSION" </dev/null 2>/dev/null) | head -1 \
    | grep -oE '[0-9]+(\.[0-9]+)+[0-9A-Za-z._+-]*' | head -1
}

ROWS="$(mktemp "${TMPDIR:-/tmp}/atlas-tools.XXXXXX")" || exit 1
trap 'rm -f "$ROWS"' EXIT
# row EVENT STEP [WHY]: one result for tools.json.
row() {
  local why="${3:-}"
  why="$(printf '%s' "$why" | tr '\t\n' '  ')"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$T_NAME" "$1" "$2" "${ver:-}" \
    "${found:-}" "$T_BIN" "${T_BIN_DIR:-}" "${T_EVERY_DAYS:-1}" "${T_STALE_DAYS:-14}" \
    "$why" >>"$ROWS"
}
good() { printf '  ok    %s\n' "$*"; }
bad()  { printf '  ----  %s\n' "$*"; failed=$((failed + 1)); }

failed=0
listing="$(plan plan 2>"$ROWS.err")"
code=$?
while IFS= read -r said; do
  [ -n "$said" ] && bad "$said"
done <"$ROWS.err"
rm -f "$ROWS.err"
[ "$code" = 0 ] || [ "$code" = 3 ] || { echo "tools.sh: toolplan did not answer" >&2; exit 1; }

# install_one: put a missing tool in, then check it. 0 when it is there.
install_one() {
  if [ -z "${T_INSTALL:-}" ]; then
    row failed install "not installed; by hand: ${T_MANUAL:-see $path}"
    bad "$T_NAME is not installed; by hand: ${T_MANUAL:-see $path}"
    return 1
  fi
  printf '%s %s: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$T_NAME" "$T_INSTALL" >>"$LOG"
  if run_tool "$T_INSTALL" && found="$(found_bin)"; then
    ver="$(version_of)"
    row installed install
    good "$T_NAME installed (${ver:-no version}) at $found"
    return 0
  fi
  row failed install "T_INSTALL failed; by hand: ${T_MANUAL:-$T_INSTALL}"
  bad "$T_NAME did not install; by hand: ${T_MANUAL:-$T_INSTALL}"
  return 1
}

check_one() {
  [ -n "${T_CHECK:-}" ] || return 0
  if run_tool "$T_CHECK"; then
    row checked check
    return 0
  fi
  row failed check "its check failed: $T_CHECK"
  bad "$T_NAME fails its check: $T_CHECK"
  return 1
}

dirs=""
declared=0
now="$(date +%s)"
while IFS="$(printf '\t')" read -r name path subjects last; do
  [ -n "$name" ] || continue
  if ! load_tool "$name" "$path"; then
    bad "$path: T_NAME must be $name and T_BIN set"
    continue
  fi
  case " ${T_ROLES:-host coding} " in *" $ROLE "*) ;; *) continue ;; esac
  declared=$((declared + 1))
  found="$(found_bin)"
  ver=""
  [ -n "$found" ] && ver="$(version_of)"
  case "$CMD" in
    list)
      printf '  %-16s %-10s %s  (%s)\n' "$name" "${ver:--}" "${found:-not installed}" "$subjects" ;;
    path)
      if [ -n "${T_BIN_DIR:-}" ]; then
        case ":$dirs:" in *":$T_BIN_DIR:"*) ;; *) dirs="${dirs:+$dirs:}$T_BIN_DIR" ;; esac
      fi ;;
    install)
      if [ -n "$found" ]; then
        row present install
        good "$name is installed (${ver:-no version})"
      else
        install_one && check_one
      fi ;;
    check)
      if [ -z "$found" ]; then
        bad "$name is not installed; bash scripts/tools.sh install"
      elif check_one; then
        good "$name works (${ver:-no version})"
      fi ;;
    update)
      if [ -z "$found" ]; then
        install_one && check_one
        continue
      fi
      # Four hours short of the days: the last try is stamped when its run
      # ended and this one began a day later, so a full day is never seen.
      every="${T_EVERY_DAYS:-1}"
      if [ "$FORCE" = 0 ] && [ "$((now - ${last:-0}))" -lt "$((every * 86400 - 14400))" ]; then
        row present update
        continue
      fi
      if [ -z "${T_UPDATE:-}" ]; then
        # Updated by hand: not a failure. tools.json notes a version that
        # moved, and brewcare names it once it is T_STALE_DAYS old.
        row manual update "by hand: ${T_MANUAL:-see $path}"
        continue
      fi
      before="$ver"
      printf '%s %s: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$name" "$T_UPDATE" >>"$LOG"
      run_tool "$T_UPDATE"
      rc=$?
      found="$(found_bin)"
      ver="$(version_of)"
      if [ "$rc" != 0 ]; then
        row failed update "T_UPDATE exited $rc"
        bad "$name did not update (exit $rc); see $LOG"
        continue
      fi
      if [ "$before" != "$ver" ]; then
        row updated update
        good "$name ${before:-?} -> ${ver:-?}"
      else
        row current update
      fi
      check_one ;;
  esac
done <<EOF
$listing
EOF

case "$CMD" in
  path) printf '%s\n' "$dirs" ;;
  list) [ "$declared" -gt 0 ] || echo "  no tool is declared for a $ROLE" ;;
  *) plan record <"$ROWS" || { echo "tools.sh: could not write tools.json" >&2; failed=$((failed + 1)); }
     echo "$declared tool(s) declared for a $ROLE, $failed problem(s)" ;;
esac
[ "$failed" = 0 ]
