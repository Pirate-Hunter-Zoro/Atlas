#!/bin/bash
# relay-pass.sh -- what the cluster's scrontab runs: one relay pass.
#
# Bash pulls, so a pushed fix reaches the cluster even when the Python it
# fixes cannot import. In order:
#   1. cd to the Atlas root; take a lock, or exit 0 when another pass holds it.
#   2. Pull only on a branch named main with no rebase, merge, cherry-pick,
#      revert or bisect outstanding. Otherwise the pass still runs, and its
#      own sync reports why.
#   3. git fetch origin main, then a fast-forward-only merge, each under
#      `timeout 60` where that exists. A failed fast-forward still runs the
#      pass: Python's sync rebases what it may and reports the rest.
#   4. When the pull changed board/, re-exec this script once, so the new
#      launcher and the new Python run.
#   5. Exec board/bin/relay --once --quiet, on $RELAY_PYTHON (the scrontab
#      entry sets it) or python3.
#
# No last-known-good copy. Bash 3.2 safe: the Mac runs it in tests, where
# `flock` and `timeout` do not exist. Everything sits inside main(), so bash
# has read the whole file before a pull rewrites it.

main() {
    local here root lock busy gitdir marker before after to branch
    here=$(cd "$(dirname "$0")" && pwd) || exit 1
    root=$(cd "$here/../.." && pwd) || exit 1
    cd "$root" || exit 1
    mkdir -p relay || exit 1

    # --- 1. one launcher at a time -------------------------------------------
    # A re-exec inherits the lock: fd 9 stays open across exec, and the
    # mkdir lock is still ours.
    lock=relay/.lock.launcher
    if command -v flock >/dev/null 2>&1; then
        if [ -z "${RELAY_PASS_REEXEC:-}" ]; then
            exec 9>>"$lock" || exit 1
            flock -n 9 || exit 0
        fi
        LOCKDIR=""
    else
        LOCKDIR="$lock.d"
        if [ -z "${RELAY_PASS_REEXEC:-}" ]; then
            if ! mkdir "$LOCKDIR" 2>/dev/null; then
                # A holder that died leaves the directory; its pid says so.
                local pid
                pid=$(cat "$LOCKDIR/pid" 2>/dev/null)
                if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                    exit 0
                fi
                rm -rf "$LOCKDIR"
                mkdir "$LOCKDIR" 2>/dev/null || exit 0
            fi
        fi
        echo $$ >"$LOCKDIR/pid"
        trap 'rm -rf "$LOCKDIR"' EXIT
    fi

    # --- 2. the busy guards, as worktree.busy_reason has them ----------------
    busy=""
    gitdir=$(git rev-parse --git-dir 2>/dev/null) || busy="not a git checkout"
    if [ -z "$busy" ]; then
        for marker in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD \
                      REVERT_HEAD BISECT_LOG; do
            if [ -e "$gitdir/$marker" ]; then
                busy="$marker"
                break
            fi
        done
    fi
    if [ -z "$busy" ]; then
        branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null)
        if [ -z "$branch" ]; then
            busy="detached HEAD"
        elif [ "$branch" != "main" ]; then
            busy="on branch $branch"
        fi
    fi

    # --- 3. a fast-forward pull -----------------------------------------------
    if [ -z "$busy" ]; then
        to=""
        if command -v timeout >/dev/null 2>&1; then
            to="timeout 60"
        fi
        before=$(git rev-parse HEAD)
        if GIT_TERMINAL_PROMPT=0 $to git fetch --quiet origin main; then
            GIT_TERMINAL_PROMPT=0 $to git merge --ff-only --quiet origin/main \
                >/dev/null 2>&1
        fi
        after=$(git rev-parse HEAD)

        # --- 4. new board code: run the new launcher, once -----------------
        if [ "$before" != "$after" ] && [ -z "${RELAY_PASS_REEXEC:-}" ] \
           && ! git diff --quiet "$before" "$after" -- board/; then
            echo "relay-pass: board/ moved ${before:0:8}..${after:0:8}; re-exec" >&2
            trap - EXIT
            RELAY_PASS_REEXEC=1 exec "${BASH:-bash}" \
                "$root/board/scripts/relay-pass.sh" "$@"
        fi
    else
        echo "relay-pass: not pulling: $busy" >&2
    fi

    # --- 5. the pass ------------------------------------------------------------
    if [ -z "$LOCKDIR" ]; then
        exec "${RELAY_PYTHON:-python3}" board/bin/relay --once --quiet
    fi
    # The mkdir lock is removed on exit, which an exec would skip.
    "${RELAY_PYTHON:-python3}" board/bin/relay --once --quiet
}

main "$@"; exit
