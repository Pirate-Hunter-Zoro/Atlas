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
# It fetches and merges the remote before pushing, so a second machine
# committing the same repository -- a compute node compiling the same document
# -- cannot wedge every later push as a non-fast-forward.
#
# The commit is authored by whoever `git config user.name` says, and carries no
# trailers, no co-authors, and no attribution to any assistant. The work is the
# repository owner's; the history should say so and nothing else.
#
# Exits 0 on success or when there was simply nothing to commit. Any other exit
# means the push did not happen, and the reason is on stdout.
# ---------------------------------------------------------------------------
set -uo pipefail

# Where the tool's own helpers are, worked out BEFORE the `cd` below: after it,
# `${BASH_SOURCE[0]}` as typed no longer resolves from the working directory.
# `tool.sh` answers where the tool is and where it sits in its repository, which
# is the question the restart block at the end of this file asks.
SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
# shellcheck source=scripts/tool.sh
. "$SCRIPTS/tool.sh"

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
#
# AND `--only` ALONE IS WRONG, which is the defect this block is a response to.
# It takes each named path's content FROM THE WORKING TREE rather than from the
# index, so a staged REMOVAL of a file that is still on disk is discarded
# without a word. That is exactly the shape of untracking a generated file --
# `git rm --cached` leaves it where the tool that reads it looks -- and on 19
# September three permission allowlists were untracked, the ignore rule
# committed, the run reported success, and all three were still tracked
# afterwards. Nothing said so; the ignore rule made it look done.
#
# So `--only` is used only when it is actually needed. If nothing outside the
# pathspec is staged -- the ordinary case for an unattended save -- a plain
# commit of the index is both isolated and correct. When something outside IS
# staged, `--only` still runs, and any removal it is about to drop is NAMED
# rather than lost.
COMMIT=(commit -m "$MSG")
if [ ${#PATHS[@]} -gt 0 ]; then
  all_staged="$(git diff --cached --name-only HEAD 2>/dev/null | sort -u)"
  in_paths="$(git diff --cached --name-only HEAD -- "${PATHS[@]}" 2>/dev/null | sort -u)"

  if [ "$all_staged" != "$in_paths" ]; then
    COMMIT=(commit --only -m "$MSG" -- "${PATHS[@]}")

    # A staged removal whose file is still on disk is the one `--only` eats.
    kept=""
    while IFS= read -r f; do
      [ -n "$f" ] || continue
      [ -e "$f" ] && kept="$kept $f"
    done <<EOF
$(git diff --cached --name-only --diff-filter=D HEAD -- "${PATHS[@]}" 2>/dev/null)
EOF

    if [ -n "$kept" ]; then
      echo "NOT UNTRACKED:$kept"
      echo "  staged for removal, still on disk, and something outside the"
      echo "  pathspec is staged -- so this commit must use --only, which takes"
      echo "  those paths from the working tree and would drop the removal."
      echo "  Nothing has been lost. Commit the removal by itself: stage only it"
      echo "  and run 'git commit' with no pathspec."
    fi
  fi
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

# Integrate the remote before pushing.
#
# Without this the script pushes blind, and the first time any other machine
# commits -- a compute node compiling the same document, say -- every push from
# this clone is rejected as a non-fast-forward, for ever, and re-tapping the
# button cannot clear it.
#
# A merge, never a rebase: nothing already committed here is rewritten.
if git rev-parse --abbrev-ref '@{upstream}' >/dev/null 2>&1; then
  # Git's own words, not a guess at them. "could not reach origin" is one
  # reason a fetch fails and it is not the common one -- a branch deleted on the
  # remote, a credential that has expired, a repository renamed -- and a save
  # that invents the reason sends whoever reads it to look at the network.
  if ! fetched="$(git fetch origin "$branch" 2>&1)"; then
    echo "could not fetch origin/$branch, so nothing was pushed:"
    printf '%s\n' "$fetched" | tail -5
    exit 1
  fi

  behind="$(git rev-list --count 'HEAD..@{upstream}' 2>/dev/null || echo 0)"
  if [ "${behind:-0}" != "0" ] && [ -n "$(git status --porcelain)" ]; then
    # A merge refuses to overwrite uncommitted work and is right to. This is the
    # pathspec case -- `ship.sh` commits `board/` while a course is part-way
    # through an afternoon -- so say why the remote is not coming in rather than
    # reporting a merge that never started.
    echo "origin/$branch is ahead and this tree has uncommitted work outside the"
    echo "  commit, so it was not merged in; the push may be rejected. Save the"
    echo "  rest, then push again."
  elif [ "${behind:-0}" != "0" ]; then
    if ! git merge --no-edit '@{upstream}'; then
      # Generated output is allowed to be resolved automatically: two machines
      # compiling one source produce two different PDFs of the same document,
      # and that is not a disagreement about anyone's work. Everything else is,
      # so it stops here rather than a script picking a winner.
      # `(^|/)build/` rather than `/build/`: a path git prints is relative to
      # the repository root, so a top-level `build/` has no slash in front of it
      # and would read as somebody's work.
      conflicts="$(git diff --name-only --diff-filter=U)"
      real="$(printf '%s\n' "$conflicts" | grep -Ev '(^|/)build/' || true)"
      if [ -n "$real" ]; then
        git merge --abort
        echo "merge conflicts outside build output; resolve by hand:"
        printf '%s\n' "$real"
        exit 1
      fi
      printf '%s\n' "$conflicts" | while IFS= read -r f; do
        [ -n "$f" ] && git checkout --ours -- "$f" && git add -- "$f"
      done
      # ABANDON THE MERGE RATHER THAN LEAVE IT STANDING. A conflict `--ours`
      # cannot take -- a file deleted on one side and edited on the other -- goes
      # no further, and a repository left with MERGE_HEAD in it is one where
      # `worktree.busy_reason` refuses every later save. That is the board's only
      # door closed from an iPad, by the thing that was meant to keep it open.
      if ! git commit --no-edit; then
        git merge --abort
        echo "the merge could not be completed, so it was abandoned and nothing"
        echo "  was pushed. The commit above is safe here. Merge by hand."
        exit 1
      fi
      echo "merged origin/$branch; kept this machine's build output"
    else
      echo "merged origin/$branch"
    fi
  fi

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
# So: did this commit touch `board/`? Asked of the commit that was just made,
# and of THE TOOL's directory rather than of this script's. `scripts` is one
# level too deep: the test was `^board/scripts/`, so a change to the board's
# Python or its pages -- which is most changes -- matched nothing and no board
# ever came back. `ship.sh` calls `tutor restart --tutors` itself and so was
# never affected; every direct caller was, which is the save button, `board
# finish` and `lesson/git.py`. See `scripts/tool.sh`.
#
# And of the RIGHT repository. One copy of this script serves every workspace,
# and `test/beside.py` runs it against throwaway repositories: a commit in a
# repository the tool does not live in cannot have changed the tool, whatever
# the commit happens to have touched.
TOOL_REL="$(tool_prefix)"
TOOL_ROOT="$(tool_root)"
if [ "$TOOL_ROOT" = "$ROOT" ] && git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null \
   | grep -q "^${TOOL_REL:+$TOOL_REL/}"; then
  echo
  echo "the tool changed, so the boards come back on the new code"
  if command -v tutor >/dev/null 2>&1; then
    tutor restart || echo "  (boards could not be restarted; run 'tutor restart' by hand)"
  else
    echo "  (tutor is not on PATH; run 'tutor restart' by hand)"
  fi
fi

exit 0
