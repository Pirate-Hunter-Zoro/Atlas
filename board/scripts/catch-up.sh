#!/usr/bin/env bash
# ===========================================================================
#  catch-up.sh -- put THIS machine right, in one command, and then say what is
#  actually true rather than what should be.
#
#      bash scripts/catch-up.sh              catch up and restart
#      bash scripts/catch-up.sh --tidy       ...and stop boards for courses
#                                            with nothing in them
#      bash scripts/catch-up.sh --report     change nothing; just say where
#                                            everything is
#
#  A fix shipped from somewhere else sits on disk here until something restarts
#  the processes holding the old code. That is two kinds of process and two kinds
#  of repository, and remembering the list is not somebody's job:
#
#    1. Atlas, which holds the tool every process reads once at startup;
#    2. the private repositories nested inside it -- each course, and
#       ai-config -- which Atlas ignores and so cannot pull for them;
#    3. the boards and the tutors, which are long-lived.
#
#  It is machine-agnostic on purpose. Run it anywhere; it works out what this
#  machine is.
#
#  NOTHING HERE CAN DESTROY WORK, and that is now a property of the commands it
#  runs rather than a set of guards around them.
#
#  Every pull is `--ff-only`: Atlas first, then each nested repository, one
#  line each. A fast-forward cannot rewrite history, cannot move a dirty tree,
#  and cannot lose a commit. The worst case is that it declines and says why.
#  A nested repository declining never stops the next; Atlas failing to pull
#  stops everything, because everything after it runs Atlas's code.
#
#  Two guards are asked of each repository before its pull, because each is
#  about something real:
#
#    * a rebase, a merge, a cherry-pick, a revert or a bisect outstanding means
#      a terminal here has its own plan for the next commit;
#    * a detached HEAD means somebody is reading around in an old commit, and
#      `origin/HEAD` exists in most clones -- so a branch name read as "HEAD"
#      would walk them onto the remote's default branch.
#
#  Nothing here resets, stashes or tags. A reset keyed on DIRTY throws away an
#  afternoon sitting on a repository that is already exactly on origin, and a
#  fast-forward has no such case.
# ===========================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# The repository root -- the directory holding `atlas.json`, one level above the
# tool. TUTORBOARD_COURSES overrides it for the test, which needs a tree of its own:
# what the loop below DOES to a repository is the part of this script worth
# testing, and it cannot be tested against the real home without doing it to the
# real home. One variable, one meaning, everywhere.
COURSES="${TUTORBOARD_COURSES:-$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null || dirname "$HERE")}"
TUTOR="$HERE/bin/tutor"
BOARD="$HERE/bin/board"

TIDY=0
REPORT=0
COURSES_ONLY=0
for a in "$@"; do
  case "$a" in
    --tidy)   TIDY=1 ;;
    --report) REPORT=1 ;;
    # The repositories and the workspaces, and nothing that touches a process:
    # no restarts, no machine report -- "put the files right and stop". The
    # test uses it; a person has no reason to.
    --courses-only) COURSES_ONLY=1 ;;
    -h|--help) sed -n '3,12p' "${BASH_SOURCE[0]}" | sed 's/^#  \{0,1\}//'; exit 0 ;;
  esac
done

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
line() { printf '   %s\n' "$*"; }

# ------------------------------------------------------------------ the log
# What ran this, and where from. It exists because a round of this script reset
# two repositories that nobody present could account for, and working out what
# had invoked it took longer than fixing what it did. One block per run,
# appended, naming the host and the whole parent chain.
CATCHUP_LOG="${TUTORBOARD_CATCHUP_LOG:-$HOME/.tutorboard-catch-up.log}"
{
  printf '%s  host=%s  pid=%s  args=%s\n' \
    "$(date '+%Y-%m-%d %H:%M:%S')" "$(hostname -s 2>/dev/null)" "$$" "${*:-none}"
  _p="${PPID:-0}"
  while [ "${_p:-0}" -gt 1 ]; do
    printf '    <- %-8s %s\n' "$_p" "$(ps -o args= -p "$_p" 2>/dev/null | head -c 200)"
    _p="$(ps -o ppid= -p "$_p" 2>/dev/null | tr -d ' ')"
  done
} >> "$CATCHUP_LOG" 2>/dev/null

# --------------------------------------------------------------- the guards
# Asked BEFORE the pull, not after it. A `git pull` into a repository somebody
# is part-way through fails with "could not pull" -- which is true, useless, and
# hides the one fact the person needs. Whether it is safe to touch a repository
# at all is the first question, not a consequence of a command already tried.
# One function, asked of Atlas and of every nested repository alike.
busy_reason() {
  local repo="$1" gitdir marker reason=""
  gitdir="$(git -C "$repo" rev-parse --git-dir 2>/dev/null)"
  case "$gitdir" in /*) ;; *) gitdir="$repo/$gitdir" ;; esac
  for marker in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD \
                REVERT_HEAD BISECT_LOG; do
    [ -e "$gitdir/$marker" ] && reason="$marker is outstanding"
  done
  if [ -z "$reason" ] && \
     [ "$(git -C "$repo" rev-parse --abbrev-ref HEAD 2>/dev/null)" = "HEAD" ]; then
    reason="HEAD is detached"
  fi
  printf '%s' "$reason"
}
BUSY="$(busy_reason "$COURSES")"

# ------------------------------------------------------------ the repository
if [ "$REPORT" -eq 0 ]; then
  say "the repository"
  if [ -n "$BUSY" ]; then
    line "$BUSY — the repository is left exactly as it is, and nothing below"
    line "this will touch it either. Finish or abort that, then run this again."
  else
  before="$(git -C "$COURSES" rev-parse HEAD 2>/dev/null)"
  if out="$(git -C "$COURSES" pull --ff-only 2>&1)"; then
    after="$(git -C "$COURSES" rev-parse HEAD 2>/dev/null)"
    if [ "$before" != "$after" ]; then
      line "pulled $(git -C "$COURSES" rev-list --count "$before".."$after") commit(s)"
      # Everything below reads this repository, so run it again on what arrived.
      line "re-running on the code that just landed"
      exec bash "$HERE/scripts/catch-up.sh" "$@"
    fi
    line "already current"
  else
    line "COULD NOT PULL — fix this first, everything else depends on it:"
    printf '%s\n' "$out" | sed 's/^/     /'
    exit 1
  fi

  # Somebody else's repositories, tracked by pointer. Only `vendor/colibri`
  # moves; `vendor/colibri-build` is pinned on purpose and a `--remote` here
  # would walk it forward under whatever is building against it.
  #
  # `--init` so a clone that forgot `--recurse-submodules` is repaired rather
  # than left with an empty vendor/, which is the first thing a new machine
  # gets wrong. Never fatal: a machine with no network still teaches.
  if [ -f "$COURSES/.gitmodules" ]; then
    if git -C "$COURSES" submodule update --init --remote --merge vendor/colibri \
         >/dev/null 2>&1; then
      line "vendor/colibri at $(git -C "$COURSES/vendor/colibri" rev-parse --short HEAD 2>/dev/null)"
    else
      line "vendor/colibri not pulled; left where it is"
    fi
    git -C "$COURSES" submodule update --init vendor/colibri-build >/dev/null 2>&1 || true
  fi
  fi
fi

# ------------------------------------------------- the nested repositories
# Each course, and ai-config, is its own private repository inside Atlas and
# ignored by it, so Atlas's pull above moves none of them. Each is pulled here,
# after the re-exec so it runs once and on the new code, and OUTSIDE Atlas's
# busy check: a rebase in Atlas is no reason to leave a course behind. The
# same two guards are asked of each one, and one line says what happened.
if [ "$REPORT" -eq 0 ]; then
  nested=()
  for dir in "$COURSES"/courses/*/ "$COURSES"/ai-config/; do
    repo="${dir%/}"
    [ -e "$repo/.git" ] && nested+=("$repo")
  done
  if [ ${#nested[@]} -gt 0 ]; then
    say "the nested repositories"
    for repo in "${nested[@]}"; do
      rel="${repo#$COURSES/}"
      why="$(busy_reason "$repo")"
      if [ -n "$why" ]; then
        line "$rel: $why — left exactly as it is"
        continue
      fi
      before="$(git -C "$repo" rev-parse HEAD 2>/dev/null)"
      if out="$(git -C "$repo" pull --ff-only 2>&1)"; then
        after="$(git -C "$repo" rev-parse HEAD 2>/dev/null)"
        if [ "$before" != "$after" ]; then
          line "$rel: pulled $(git -C "$repo" rev-list --count "$before".."$after") commit(s)"
        else
          line "$rel: already current"
        fi
      else
        line "$rel: not pulled — $(printf '%s\n' "$out" | grep -v '^hint:' | tail -1)"
      fi
    done
  fi
fi

# -------------------------------------------------------- the workspaces
# Every repository was pulled above. This says, per workspace, what is still
# uncommitted -- asked of the repository that OWNS the workspace, because Atlas
# ignores courses/*/ and asking Atlas about a course says "current" over any
# amount of somebody's afternoon. Nothing here moves anything: uncommitted work
# is reported and left where it is.
if [ "$REPORT" -eq 0 ]; then
  say "the workspaces"

  # What is actually uncommitted, per workspace, not counting the board's own
  # scratch. A running board writes into `live/` continuously and none of it is
  # work anybody meant to keep, so counting it made every workspace with a
  # board on it look like it needed rescuing.
  for dir in "$COURSES"/*/*/; do
    root="${dir%/}"
    [ -d "$root" ] || continue
    # A workspace, by the same test the board uses.
    if [ ! -f "$root/tutorboard.json" ] && [ ! -f "$root/AI_INSTRUCTIONS.md" ] \
       && [ ! -d "$root/live" ]; then
      continue
    fi
    rel="${root#$COURSES/}"
    # A course with no .git of its own is files Atlas ignores, so asking git
    # about it would say "current" over everything in it. It is named instead,
    # with the command that adopts it in place.
    case "$rel" in
      courses/*)
        if [ ! -e "$root/.git" ]; then
          line "$rel: not its own repository, so nothing in it is tracked -- bash board/bootstrap.sh"
          continue
        fi ;;
    esac
    # `-C "$root"` with the pathspec `.`: git finds the repository that holds
    # the workspace -- Atlas, or the course's own -- and lists only what is
    # under it. Porcelain paths are relative to THAT repository's root, so in a
    # course `live/` has no slash in front of it; the path is cut out of the
    # line and the scratch rule anchored on either.
    dirty="$(git -C "$root" status --porcelain -- . 2>/dev/null | cut -c4- \
             | grep -Ev '(^|/)live/' || true)"
    n="$(printf '%s' "$dirty" | grep -c . || true)"
    if [ "${n:-0}" -gt 0 ]; then
      line "$rel: $n uncommitted file(s), left where they are"
    else
      line "$rel: current"
    fi
  done
fi

# ------------------------------------------------------------- the processes
if [ "$REPORT" -eq 0 ] && [ "$COURSES_ONLY" -eq 0 ]; then
  say "the boards and the tutors"
  # `tutor restart --tutors` owns what is safe to touch: boards answering on this
  # machine, and daemons that are not mid-turn. A board that comes back on the
  # current code publishes itself on the tailnet, which is what makes another
  # machine able to see it at all.
  "$TUTOR" restart --tutors 2>&1 | sed 's/^/   /'
fi

# ------------------------------------------------------- stop the empty ones
if [ "$TIDY" -eq 1 ]; then
  say "boards with nothing in them"
  for dir in "$COURSES"/*/*/; do
    root="${dir%/}"
    [ -d "$root/live/cards" ] || continue
    [ -f "$root/live/.board.json" ] || continue
    n="$(find "$root/live/cards" -maxdepth 1 -name '[0-9][0-9][0-9][0-9]-*' 2>/dev/null | wc -l | tr -d ' ')"
    if [ "$n" = "0" ]; then
      ( cd "$root" && "$BOARD" stop >/dev/null 2>&1 ) \
        && line "$(basename "$root"): stopped (no lesson in it)"
    fi
  done
fi

# ------------------------------------------------------------------ the truth
if [ "$COURSES_ONLY" -eq 1 ]; then
  exit 0
fi

say "what is actually running here"
"$TUTOR" where 2>&1 | sed 's/^/   /'

say "how to reach each of them"
TUTORBOARD_COURSES="$COURSES" python3 - "$COURSES" "$HERE" <<'PY'
import json, os, sys
sys.path.insert(0, sys.argv[2])
from tutorboard import machine, processes
from tutorboard.net import tailscale

from tutorboard import atlas

me = tailscale.tailnet_self() or machine.node_name()
# `atlas.workspaces()` rather than a listing, so this says exactly what the
# board says: same walk, same two levels, vendor skipped. A report that
# disagrees with the thing it is reporting on is worse than no report.
for w in atlas.workspaces():
    rec = os.path.join(w["root"], "live", ".board.json")
    if not os.path.isfile(rec):
        continue
    try:
        with open(rec, encoding="utf-8") as fh:
            info = json.load(fh)
    except (OSError, ValueError):
        continue
    if not processes.board_is_running(info.get("pid"), w["root"]):
        continue
    print("   %-30s http://%s:%s/" % (w["id"], me, info.get("port")))
print()
print("   the installed app's address serves the workspace that was last chosen")
print("   on this machine. The URLs above reach one board each, directly.")
PY

printf '\n'
say "if the app still opens the wrong course"
line "The address opens whichever board holds the tailnet name. A tap in the hub"
line "takes it, and so does \`board vpn serve\` in a course:"
line ""
line "    cd <course> && board vpn serve"
line ""
line "\`board net\` says where the name points now."
