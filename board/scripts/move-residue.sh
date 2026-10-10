#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# move-residue.sh -- carry what git left behind from <old> into <new>.
#
#   board/scripts/move-residue.sh <old> <new>            dry run: print the plan
#   board/scripts/move-residue.sh <old> <new> --apply    move it
#
# After a commit moves a subject's tracked files (research/X -> projects/X),
# the ignored residue stays at <old>: phi/, results/, .env, .venv, caches.
# This moves it beside the tracked files, by rename only.
#
# Refuses, moving nothing, unless:
#   * <new> holds tracked files and <old> holds none (the git move came first);
#   * <old>, <new> and every entry to move sit on one filesystem, so each move
#     is a rename and never a copy of patient data;
#   * no entry collides with one already at <new>.
#
# Entries are listed by name only. A directory present on both sides is merged
# by descending into it, except a directory named in tutorboard/fenced.py
# NEVER (phi, data, inbox, ...): nothing below one is ever listed, so it moves
# whole or collides. A moved `.env` has the old absolute prefix rewritten in
# its path values; only the changed key names are printed. Emptied directories
# are removed with rmdir, up to and including an emptied research/ or practice/.
#
# The log is tab-separated, in order, so a rollback reverses it bottom-up:
#   moved <src> <dst>     reverse with: mv -n <dst> <src>
#   env   <file> <KEY>    reverse by swapping the prefixes back
#   rmdir <dir>           reverse with: mkdir <dir>
#
# Runs on the cluster and on the Mac's bash 3.2.
# ---------------------------------------------------------------------------
set -uo pipefail

NEVER="phi data inbox stage1 stage2 raw audio"

die() { echo "move-residue: $*" >&2; exit 1; }

usage() {
    echo "usage: move-residue.sh <old> <new> [--apply]" >&2
    exit 2
}

APPLY=0
ARGS=()
for a in "$@"; do
    case "$a" in
        --apply) APPLY=1 ;;
        -h|--help) usage ;;
        -*) usage ;;
        *) ARGS[${#ARGS[@]}]="$a" ;;
    esac
done
[ "${#ARGS[@]}" -eq 2 ] || usage

[ -d "${ARGS[0]}" ] && [ ! -L "${ARGS[0]}" ] || die "not a directory: ${ARGS[0]}"
[ -d "${ARGS[1]}" ] && [ ! -L "${ARGS[1]}" ] || die "not a directory: ${ARGS[1]}"
OLD="$(cd "${ARGS[0]}" && pwd -P)" || die "cannot enter ${ARGS[0]}"
NEW="$(cd "${ARGS[1]}" && pwd -P)" || die "cannot enter ${ARGS[1]}"
# The logical spellings too: a .env written on the cluster may name the path
# through a symlink.
OLD_L="$(cd "${ARGS[0]}" && pwd -L)"
NEW_L="$(cd "${ARGS[1]}" && pwd -L)"

[ "$OLD" != "$NEW" ] || die "<old> and <new> are the same directory"
case "$NEW/" in "$OLD"/*) die "<new> is inside <old>" ;; esac
case "$OLD/" in "$NEW"/*) die "<old> is inside <new>" ;; esac

# --- git: the tracked files moved first ------------------------------------
TOP="$(git -C "$NEW" rev-parse --show-toplevel 2>/dev/null)" \
    || die "<new> is not inside a git work tree"
TOP="$(cd "$TOP" && pwd -P)"
[ -n "$(git -C "$NEW" ls-files -- . 2>/dev/null | head -n 1)" ] \
    || die "<new> holds no tracked files: move the tracked files with git first"
if git -C "$OLD" rev-parse --git-dir >/dev/null 2>&1 \
        && [ -n "$(git -C "$OLD" ls-files -- . 2>/dev/null | head -n 1)" ]; then
    die "<old> still holds tracked files: move them with git first"
fi

# --- one filesystem ----------------------------------------------------------
# GNU stat takes -c; BSD stat takes -f, where GNU's -f means something else.
if stat -c %d / >/dev/null 2>&1; then
    dev_of() { stat -c %d "$1" 2>/dev/null; }
else
    dev_of() { stat -f %d "$1" 2>/dev/null; }
fi
OLD_DEV="$(dev_of "$OLD")"
NEW_DEV="$(dev_of "$NEW")"
[ -n "$OLD_DEV" ] && [ -n "$NEW_DEV" ] || die "cannot read device ids"
[ "$OLD_DEV" = "$NEW_DEV" ] \
    || die "<old> and <new> are on different filesystems; refusing to copy"

# --- the plan --------------------------------------------------------------
SRC=()       # entries to move, in order
DST=()
MERGED=()    # directories descended into, parents before children
PROBLEMS=()

fenced() {
    local low
    low="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
    case " $NEVER " in *" $low "*) return 0 ;; esac
    return 1
}

plan() {   # plan <dir under OLD> <matching dir under NEW>
    local from="$1" to="$2" path name
    while IFS= read -r -d '' path; do
        name="${path##*/}"
        if [ ! -e "$to/$name" ] && [ ! -L "$to/$name" ]; then
            if [ "$(dev_of "$path")" != "$OLD_DEV" ]; then
                PROBLEMS[${#PROBLEMS[@]}]="on another filesystem: $path"
            else
                SRC[${#SRC[@]}]="$path"
                DST[${#DST[@]}]="$to/$name"
            fi
        elif [ -d "$path" ] && [ ! -L "$path" ] && [ -d "$to/$name" ] \
                && [ ! -L "$to/$name" ] && ! fenced "$name"; then
            MERGED[${#MERGED[@]}]="$path"
            plan "$path" "$to/$name"
        else
            PROBLEMS[${#PROBLEMS[@]}]="collision: $to/$name exists"
        fi
    done < <(find "$from" -mindepth 1 -maxdepth 1 -print0 | LC_ALL=C sort -z)
}

plan "$OLD" "$NEW"

if [ "${#PROBLEMS[@]}" -gt 0 ]; then
    i=0
    while [ "$i" -lt "${#PROBLEMS[@]}" ]; do
        echo "move-residue: ${PROBLEMS[$i]}" >&2
        i=$((i + 1))
    done
    die "refused: nothing moved"
fi

# --- .env path values ----------------------------------------------------------
# Rewrites `<file>`'s values that are, or start with, an old absolute prefix.
# Prints the changed keys, one per line. With a second argument, writes there.
# Every unchanged line is copied byte for byte.
env_rewrite() {
    local file="$1" out="${2:-}" line rest key pre val q body nl pair from to endq
    while true; do
        nl=1
        if ! IFS= read -r line; then
            [ -n "$line" ] || break
            nl=0
        fi
        rest="$line"
        case "$rest" in
            [A-Za-z_]*=*|"export "[A-Za-z_]*=*)
                pre="${rest%%=*}="
                key="${pre%=}"; key="${key#export }"
                val="${rest#*=}"
                q=""
                case "$val" in
                    \"*) q='"' ;;
                    \'*) q="'" ;;
                esac
                body="${val#"$q"}"
                endq=""
                if [ -n "$q" ]; then
                    case "$body" in *"$q") body="${body%"$q"}"; endq="$q" ;; esac
                fi
                for pair in "$OLD|$NEW" "$OLD_L|$NEW_L"; do
                    from="${pair%%|*}"; to="${pair#*|}"
                    case "$body" in
                        "$from"|"$from"/*)
                            line="$pre$q$to${body#"$from"}$endq"
                            echo "$key" >&3
                            break ;;
                    esac
                done ;;
        esac
        if [ -n "$out" ]; then
            if [ "$nl" -eq 1 ]; then printf '%s\n' "$line"; else printf '%s' "$line"; fi
        fi
        [ "$nl" -eq 1 ] || break
    done < "$file"
}

env_keys() {   # env_keys <file>: the keys a rewrite would change
    env_rewrite "$1" 3>&1 >/dev/null
}

# --- dry run -------------------------------------------------------------------
if [ "$APPLY" -ne 1 ]; then
    i=0
    while [ "$i" -lt "${#SRC[@]}" ]; do
        printf 'would move\t%s\t%s\n' "${SRC[$i]}" "${DST[$i]}"
        if [ "${SRC[$i]##*/}" = ".env" ] && [ -f "${SRC[$i]}" ] && [ ! -L "${SRC[$i]}" ]; then
            env_keys "${SRC[$i]}" | while IFS= read -r k; do
                printf 'would rewrite\t%s\t%s\n' "${DST[$i]}" "$k"
            done
        fi
        i=$((i + 1))
    done
    echo "dry run: ${#SRC[@]} to move, nothing changed; pass --apply to move"
    exit 0
fi

# --- apply ---------------------------------------------------------------------
i=0
while [ "$i" -lt "${#SRC[@]}" ]; do
    s="${SRC[$i]}"; d="${DST[$i]}"
    if [ -e "$d" ] || [ -L "$d" ]; then
        die "collision appeared during the move: $d exists (moves so far are logged above)"
    fi
    mv -n "$s" "$d" || die "mv failed: $s (moves so far are logged above)"
    if [ -e "$s" ] || [ -L "$s" ] || { [ ! -e "$d" ] && [ ! -L "$d" ]; }; then
        die "mv did not move $s (moves so far are logged above)"
    fi
    printf 'moved\t%s\t%s\n' "$s" "$d"
    if [ "${d##*/}" = ".env" ] && [ -f "$d" ] && [ ! -L "$d" ]; then
        keys="$(env_keys "$d")"
        if [ -n "$keys" ]; then
            tmp="$(mktemp "${d%/*}/.env.move-residue.XXXXXX")" || die "mktemp failed"
            env_rewrite "$d" "$tmp" 3>/dev/null > "$tmp" \
                && cat "$tmp" > "$d" && rm -f "$tmp" \
                || { rm -f "$tmp"; die "could not rewrite $d"; }
            printf '%s\n' "$keys" | while IFS= read -r k; do
                printf 'env\t%s\t%s\n' "$d" "$k"
            done
        fi
    fi
    i=$((i + 1))
done

# Emptied directories: merged ones deepest first, then <old>, then its parents
# up to the repository's top (research/, practice/). rmdir never removes a
# directory that still holds anything.
i=$((${#MERGED[@]} - 1))
while [ "$i" -ge 0 ]; do
    rmdir "${MERGED[$i]}" 2>/dev/null && printf 'rmdir\t%s\n' "${MERGED[$i]}"
    i=$((i - 1))
done
dir="$OLD"
while [ "$dir" != "$TOP" ] && [ "$dir" != "/" ]; do
    case "$dir" in "$TOP"/*) ;; *) break ;; esac
    rmdir "$dir" 2>/dev/null || break
    printf 'rmdir\t%s\n' "$dir"
    dir="${dir%/*}"
done

if [ -e "$OLD" ]; then
    echo "done: ${#SRC[@]} moved; $OLD still holds something" >&2
else
    echo "done: ${#SRC[@]} moved; $OLD is gone"
fi
