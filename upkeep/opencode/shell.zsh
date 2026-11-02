# OpenCode front ends. Sourced from the upkeep block in ~/.zprofile.
# Exports the flags in ./env, and defines oc (TUI) and ocrun (one prompt) that attach to the
# persistent server (com.mikeyferguson.opencode-serve) so wakeups, monitors and background
# work outlive the client. With the server down they run a plain local opencode instead.

_parity_dir=${${(%):-%x}:A:h}
if [[ -r $_parity_dir/env ]]; then
  while IFS= read -r _parity_line; do
    [[ $_parity_line == [A-Z_]*=* ]] && export "$_parity_line"
  done < $_parity_dir/env
fi
unset _parity_dir _parity_line

: ${OPENCODE_SERVER_URL:=http://127.0.0.1:4096}
export OPENCODE_SERVER_URL

_oc_server_up() {
  curl -fsS -m 2 -o /dev/null "$OPENCODE_SERVER_URL/global/health" 2>/dev/null
}

oc() {
  if _oc_server_up; then
    opencode attach "$OPENCODE_SERVER_URL" --dir "$PWD" "$@"
  else
    print -u2 "oc: server at $OPENCODE_SERVER_URL is down; running a local opencode (background work ends when it exits)"
    opencode "$@"
  fi
}

ocrun() {
  if _oc_server_up; then
    opencode run --attach "$OPENCODE_SERVER_URL" --dir "$PWD" "$@"
  else
    print -u2 "ocrun: server at $OPENCODE_SERVER_URL is down; running a local opencode"
    opencode run "$@"
  fi
}
