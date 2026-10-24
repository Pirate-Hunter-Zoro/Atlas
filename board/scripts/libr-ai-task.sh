#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# libr-ai-task.sh -- one `libr-ai` request, run inside its Slurm job.
#
#   bash board/scripts/libr-ai-task.sh <subject dir> <brief file> <model>
#
# The relay submits this (tutorboard/libr_ai.py). It runs opencode once,
# unattended, against IT's model server in the subject's directory, under
# libr-ai-task.json: no shell, no edits, no web, nothing outside the subject.
# Its stdout is the model's answer, which the relay reports.
#
# IT's server keeps every chat, so this refuses again what the relay already
# refused: a subject whose tutorboard.json does not say "phi": false, and a
# directory ai-config's policy fences. Both fail closed.
# ---------------------------------------------------------------------------
set -uo pipefail

WS="${1:?subject dir}"
BRIEF="${2:?brief file}"
MODEL="${3:?model}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEY="$HOME/.config/libr-ai/key"

relay() { printf 'RELAY: %s\n' "$*" >&2; }

cd "$WS" || { relay "the subject directory is gone"; exit 2; }
if ! python3 -c 'import json,sys; sys.exit(0 if json.load(open("tutorboard.json")).get("phi") is False else 1)' 2>/dev/null; then
  relay "refused: this subject's tutorboard.json does not say phi is false"
  exit 3
fi
ATLAS="$(git rev-parse --show-toplevel 2>/dev/null || true)"
ASKS="$ATLAS/ai-config/adapters/generic.py"
if [ -z "$ATLAS" ] || [ ! -r "$ASKS" ]; then
  relay "refused: no PHI policy (ai-config/adapters/generic.py) to ask"
  exit 3
fi
if ! python3 "$ASKS" --path "$PWD/" >/dev/null 2>&1; then
  relay "refused: the PHI policy fences this directory"
  exit 3
fi
[ -s "$KEY" ] || { relay "no key at ~/.config/libr-ai/key"; exit 2; }

# opencode lives under nvm, which a batch job's shell has not loaded.
if ! command -v opencode >/dev/null 2>&1 && [ -s "$HOME/.nvm/nvm.sh" ]; then
  . "$HOME/.nvm/nvm.sh" >/dev/null 2>&1
fi
command -v opencode >/dev/null 2>&1 || { relay "no opencode on this node"; exit 2; }

# Only this config: an empty config home hides the global one and its
# plugins, and the sessions get a store of their own.
CONF_HOME="$(mktemp -d)"
trap 'rm -rf "$CONF_HOME"' EXIT
export XDG_CONFIG_HOME="$CONF_HOME"
export XDG_DATA_HOME="$HOME/.local/share/libr-ai-tasks"
export OPENCODE_CONFIG="$HERE/libr-ai-task.json"
mkdir -p "$XDG_DATA_HOME"

PROMPT="This is a task from the owner, sent through a queue. Nobody is watching,
so do not stop to ask: do it and answer. You may read the files in this
directory and nothing else; you cannot edit or run anything. Your whole reply
is what the owner receives, so make it the answer itself, and cite files as
path#Lline.

The task:

$(cat "$BRIEF")"

opencode run -m "libr-ai/$MODEL" -- "$PROMPT"
code=$?
[ "$code" -eq 0 ] || relay "opencode exited $code"

n="$(git status --porcelain --untracked-files=no -- . | wc -l | tr -d ' ')"
if [ "$n" -ne 0 ]; then
  relay "the task changed $n tracked path(s), which it may not; they stay on the cluster, uncommitted"
  exit 4
fi
exit "$code"
