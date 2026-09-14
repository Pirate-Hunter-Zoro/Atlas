#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# save-and-push.sh -- commit and push this repository.
#
#   scripts/save-and-push.sh ["commit message"]
#   scripts/save-and-push.sh "message" -- board board/scripts
#
# Run at the end of a session, usually from the board's "push" button rather
# than by hand.
#
# With no pathspec it commits EVERYTHING, which is what the board's save button
# means: save means save, and a save that left the afternoon's code behind
# because it was not the lesson would be the wrong kind of clever.
#
# With a pathspec after `--` it commits only those paths. There is one
# repository now, holding nine workspaces and the tool, so `ship.sh` uses this
# to push a change to the TOOL without sweeping up whatever somebody is
# part-way through in a course. That distinction did not exist while the tool
# was its own clone, and it is the whole reason this option is here.
#
# The commit is authored by whoever `git config user.name` says, and carries no
# trailers, no co-authors, and no attribution to any assistant. The work is the
# repository owner's; the history should say so and nothing else.
#
# Exits 0 on success or when there was simply nothing to commit. Any other exit
# means the push did not happen, and the reason is on stdout.
# ---------------------------------------------------------------------------
set -uo pipefail

# THE REPOSITORY THIS WAS RUN IN, and that emphasis is the whole of a defect
# this script had for about an hour on 14 September.
#
# It used to derive the root from the SCRIPT'S OWN LOCATION, which was right
# while the tool was its own clone and the script only ever pushed itself. It is
# wrong now: `lesson/git.py` calls this one copy of the script for every
# workspace, so a location-derived root means every save commits the repository
# the TOOL is in, whatever repository the caller meant. `test/beside.py` builds a
# throwaway repository, taps save on it, and three of its runs committed the real
# Atlas instead -- under the test's own message, "tapping: saved from the board".
#
# So: the working directory decides, and the caller sets it. A commit belongs to
# the repository somebody is standing in.
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" || { echo "cannot enter $ROOT"; exit 1; }

MSG="${1:-lesson complete}"
shift || true
# Everything after `--` is a pathspec: commit only these paths.
PATHS=()
if [ "${1:-}" = "--" ]; then
  shift
  PATHS=("$@")
fi

# Never sit waiting on a credential prompt nobody can see: fail and say so.
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=/bin/false

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "not a git repository: $ROOT"
  exit 1
}

# Never commit into an operation somebody started in a terminal. This script is
# run unattended -- from the board's save button, from `board finish`, from
# ship.sh -- and a repository part-way through a rebase or a merge has its own
# plan for its next commit. Say what is in the way and change nothing; the same
# rule lives in `tutorboard/worktree.py` for everything on the Python side.
GITDIR="$(git rev-parse --git-dir)"
for marker in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD \
              REVERT_HEAD BISECT_LOG; do
  if [ -e "$GITDIR/$marker" ]; then
    echo "$marker is outstanding in this repository, so nothing was committed."
    echo "Finish or abort it, then save again. Nothing has been lost."
    exit 1
  fi
done
if [ "$(git rev-parse --abbrev-ref HEAD)" = "HEAD" ]; then
  echo "HEAD is detached here, so a commit would be reachable from nothing."
  echo "Check out a branch, then save again. Nothing has been lost."
  exit 1
fi

# A clone has to opt into tracked hooks once. Do it here rather than making
# anyone remember, so the attribution stripper is on from the first commit.
if [ -d "$ROOT/.githooks" ] && [ -z "$(git config core.hooksPath || true)" ]; then
  git config core.hooksPath .githooks
  echo "enabled .githooks for this clone"
fi

if [ ${#PATHS[@]} -gt 0 ]; then
  git add -A -- "${PATHS[@]}" || { echo "git add failed"; exit 1; }
else
  git add -A || { echo "git add failed"; exit 1; }
fi

# `--only` with the pathspec, not a bare commit: `git commit` commits the
# INDEX, all of it, so a commit meant to carry one directory would also carry
# whatever somebody had staged in a terminal a moment earlier. The same rule
# `tutorboard/worktree.py` states for the transcript beat, and the same reason.
COMMIT=(commit -m "$MSG")
if [ ${#PATHS[@]} -gt 0 ]; then
  COMMIT=(commit --only -m "$MSG" -- "${PATHS[@]}")
fi

if git diff --cached --quiet; then
  echo "nothing to commit"
  ahead="$(git rev-list --count @{upstream}..HEAD 2>/dev/null || echo 0)"
  [ "$ahead" = "0" ] && { echo "already up to date"; exit 0; }
  echo "$ahead commit(s) not yet pushed; pushing those"
else
  git "${COMMIT[@]}" || { echo "git commit failed"; exit 1; }
  echo "committed: $MSG"
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "committed locally; no 'origin' remote to push to"
  exit 0
fi

branch="$(git rev-parse --abbrev-ref HEAD)"
if git rev-parse --abbrev-ref '@{upstream}' >/dev/null 2>&1; then
  out="$(git push 2>&1)"
else
  out="$(git push -u origin "$branch" 2>&1)"
fi
status=$?

if [ $status -ne 0 ]; then
  echo "push failed:"
  echo "$out" | tail -5
  exit $status
fi

echo "pushed $branch to origin"

# A board is a long-lived process that read serve.py when it started, so a change
# to this tool does not reach a course until its board comes back. The pages are
# served from disk and look new while the endpoints behind them are still the old
# ones -- a difference that is invisible from the outside and costs an evening to
# find. So changing the tool restarts the boards it drives.
#
# Only a push that CHANGED THE TOOL does this. It used to be decided by the
# repository's name -- `basename` of the toplevel being "Tutor-Board" -- which
# was exactly right while the tool was its own clone and is exactly wrong now
# that every push is a push of Atlas. Left alone it would bounce every board on
# the machine every time somebody saved a Galois Theory lesson, which is a
# restart in the middle of a lesson for no reason at all.
#
# So: did this commit touch `board/`? Asked of the commit that was just made.
TOOL_REL="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-prefix 2>/dev/null)"
TOOL_REL="${TOOL_REL%/}"
if [ -n "$TOOL_REL" ] && git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null \
   | grep -q "^$TOOL_REL/"; then
  if command -v tutor >/dev/null 2>&1; then
    echo
    echo "the tool changed, so the boards come back on the new code"
    tutor restart || echo "  (boards could not be restarted; run 'tutor restart' by hand)"
  fi
fi

exit 0
