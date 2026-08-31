#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# save-and-push.sh -- commit everything in this repository and push it.
#
#   scripts/save-and-push.sh ["commit message"]
#
# Run at the end of a session, usually from the board's "push" button rather
# than by hand.
#
# The commit is authored by whoever `git config user.name` says, and carries no
# trailers, no co-authors, and no attribution to any assistant. The work is the
# repository owner's; the history should say so and nothing else.
#
# Exits 0 on success or when there was simply nothing to commit. Any other exit
# means the push did not happen, and the reason is on stdout.
# ---------------------------------------------------------------------------
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || { echo "cannot enter $ROOT"; exit 1; }

MSG="${1:-lesson complete}"

# Never sit waiting on a credential prompt nobody can see: fail and say so.
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=/bin/false

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "not a git repository: $ROOT"
  exit 1
}

# A clone has to opt into tracked hooks once. Do it here rather than making
# anyone remember, so the attribution stripper is on from the first commit.
if [ -d "$ROOT/.githooks" ] && [ -z "$(git config core.hooksPath || true)" ]; then
  git config core.hooksPath .githooks
  echo "enabled .githooks for this clone"
fi

git add -A || { echo "git add failed"; exit 1; }

if git diff --cached --quiet; then
  echo "nothing to commit"
  ahead="$(git rev-list --count @{upstream}..HEAD 2>/dev/null || echo 0)"
  [ "$ahead" = "0" ] && { echo "already up to date"; exit 0; }
  echo "$ahead commit(s) not yet pushed; pushing those"
else
  git commit -m "$MSG" || { echo "git commit failed"; exit 1; }
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
  if ! git fetch origin "$branch" 2>&1; then
    echo "could not reach origin to fetch; not pushing"
    exit 1
  fi

  behind="$(git rev-list --count 'HEAD..@{upstream}' 2>/dev/null || echo 0)"
  if [ "${behind:-0}" != "0" ]; then
    if ! git merge --no-edit '@{upstream}'; then
      # Generated output is allowed to be resolved automatically: two machines
      # compiling one source produce two different PDFs of the same document,
      # and that is not a disagreement about anyone's work. Everything else is,
      # so it stops here rather than a script picking a winner.
      conflicts="$(git diff --name-only --diff-filter=U)"
      real="$(printf '%s\n' "$conflicts" | grep -v '/build/' || true)"
      if [ -n "$real" ]; then
        git merge --abort
        echo "merge conflicts outside build output; resolve by hand:"
        printf '%s\n' "$real"
        exit 1
      fi
      printf '%s\n' "$conflicts" | while IFS= read -r f; do
        [ -n "$f" ] && git checkout --ours -- "$f" && git add -- "$f"
      done
      git commit --no-edit || { echo "could not complete merge"; exit 1; }
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
exit 0
