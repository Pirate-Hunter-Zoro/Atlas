# ---------------------------------------------------------------------------
# rebuild-alias.sh -- the `rebuild` command, for a shell profile.
#
# SOURCED, not run. Add this to ~/.bashrc or ~/.zshrc, with the path of
# your own checkout (~/Atlas on the cluster, ~/Developer/Atlas on the Mac):
#
#   if [ -r "$HOME/Developer/Atlas/projects/Paper-Writer/config/rebuild-alias.sh" ]; then
#       . "$HOME/Developer/Atlas/projects/Paper-Writer/config/rebuild-alias.sh"
#   fi
#
# That line in the profile is the only place the checkout's path is written.
# The function finds rebuild-docs.sh from where this file was sourced, so
# nothing in here names a home-relative path.
#
# Then, from anywhere inside a paper repository, after editing a Markdown file:
#
#   rebuild                 rebuild what changed, in the repository you are in
#   rebuild --all           rebuild every document in it
#   rebuild --list          say what would be rebuilt, do nothing
#   rebuild path/to/one.md  rebuild one document
#
# It lives in the repository rather than in the profile so it stays tracked in
# git, which is the same reason `libr-local-llm/config/opencode-guard.sh` does.
# A profile is the one file on a machine nobody has a copy of.
#
# **A function, not an alias.** An alias cannot both default to the current
# directory and pass a path through: `alias rebuild='rebuild-docs.sh .'` turns
# `rebuild some/paper` into two targets, and quietly rebuilds the whole
# repository alongside the folder you named.
#
# Rename it by editing the one word below. It is defined unconditionally
# because defining a function costs nothing and writes nothing, but it names
# the problem rather than reporting "no such file" if this checkout moves.
# ---------------------------------------------------------------------------

# Where this file is, asked of the shell that sources it: bash says so in
# BASH_SOURCE, zsh in the %x prompt escape (behind eval, because bash cannot
# parse that expansion). It is resolved once, now, since a function's own
# BASH_SOURCE later names this file but zsh's %x would name the caller.
if [ -n "${BASH_VERSION:-}" ]; then
    _rebuild_alias_file=${BASH_SOURCE[0]}
elif [ -n "${ZSH_VERSION:-}" ]; then
    eval '_rebuild_alias_file=${(%):-%x}'
else
    _rebuild_alias_file=
fi
_REBUILD_DOCS_SCRIPT=
if [ -n "$_rebuild_alias_file" ]; then
    _REBUILD_DOCS_SCRIPT="$(cd "$(dirname "$_rebuild_alias_file")/.." 2>/dev/null && pwd -P)/scripts/rebuild-docs.sh"
fi
unset _rebuild_alias_file

rebuild() {
    local script="$_REBUILD_DOCS_SCRIPT"
    if [ -z "$script" ] || [ ! -r "$script" ]; then
        echo "rebuild: not found: ${script:-(this shell could not say where rebuild-alias.sh was sourced from)}" >&2
        echo "rebuild: if the checkout moved, fix the path your shell profile" \
             "sources rebuild-alias.sh from." >&2
        return 127
    fi
    # Arguments pass straight through. The script defaults to the repository
    # you are standing in, which is the only reason this can be one word --
    # and putting that default HERE instead was wrong: `rebuild --list` has an
    # argument, so nothing would have supplied the missing path.
    # Through bash rather than by its execute bit: git tracks the script as
    # 100644, so a fresh clone has no bit to rely on.
    bash "$script" "$@"
}
