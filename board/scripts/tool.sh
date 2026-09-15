# ---------------------------------------------------------------------------
# tool.sh -- where the tool is, and where it sits inside its repository.
#
# SOURCED, not run. `save-and-push.sh` and `ship.sh` both need the same answer
# and for a while worked it out two ways, one of which was wrong: it asked git
# about `scripts/` rather than about the tool, so the commit test was
# `^board/scripts/` and a change to `board/tutorboard/` or `board/web/` matched
# nothing. The pages were served new from disk while the endpoints behind them
# stayed old, which is invisible from the outside and costs an evening.
#
# One derivation, read twice. Everything here is a function so that the answer
# is worked out when it is asked for rather than when this file is read.
# ---------------------------------------------------------------------------

# The tool's own directory -- `board`, the parent of the one this file is in.
#
# ABSOLUTE, AND RESOLVED FROM THIS FILE. A caller that has already changed
# directory gets the same answer, which is the second half of the same defect:
# `${BASH_SOURCE[0]}` is the path as it was typed, and `save-and-push.sh` cd's
# to the repository root before it asks. Run as
# `cd board && bash scripts/save-and-push.sh`, a relative `git -C scripts` was
# then resolved against the root, failed, and skipped the restart in silence.
tool_dir() {
  ( cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd -P )
}

# The repository the TOOL is in, which is not always the one being committed:
# `lesson/git.py` runs this one copy of the script for every workspace, and the
# board's test suite runs it against throwaway repositories. A commit in a
# different repository cannot have touched the tool, and the caller has to be
# able to tell.
tool_root() {
  local here
  here="$(tool_dir)" || return 1
  [ -n "$here" ] || return 1
  git -C "$here" rev-parse --show-toplevel 2>/dev/null
}

# The tool's path inside its own repository, with no trailing slash: `board`.
#
# Empty is a real answer and means the tool IS the repository root -- which is
# how the board's own suites lay out a sandbox, and how this looked while the
# tool was its own clone. Every commit touches the tool in that case, and the
# callers say so rather than treating the empty string as a failure.
tool_prefix() {
  local here rel
  here="$(tool_dir)" || return 1
  [ -n "$here" ] || return 1
  rel="$(git -C "$here" rev-parse --show-prefix 2>/dev/null)" || return 1
  printf '%s' "${rel%/}"
}
