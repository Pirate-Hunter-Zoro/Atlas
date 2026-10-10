#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup.sh -- build every workspace's environment, on whichever machine this is.
#
#     bash scripts/setup.sh
#
# 1. The system tools. On a Mac, `brew bundle` on the root Brewfile, installing
#    what is missing and moving nothing that is there (--no-upgrade). Elsewhere,
#    uv is installed into ~/.local/bin and the latest stable Go into ~/.local/go
#    (linked from ~/.local/bin) when either is not on the PATH; nothing needs
#    root, since the cluster has no Go module. Lean's elan is the Lean
#    workspace's own setup's to install.
# 2. Every workspace, found the way the board finds them (`subjects.all`),
#    never from a list. ai-config, the one private repository nested in Atlas,
#    is reported when this machine has not cloned it. A workspace is built by
#    what it holds:
#      pyproject.toml   uv sync, with the `test` extra, and the `cluster` extra
#                       only where Slurm exists
#      lean-toolchain   its own scripts/setup.sh: elan, the toolchain, the
#                       Mathlib cache, the build
#      go.mod           go mod download
#
# Idempotent: a second run changes nothing and says so. One line per workspace;
# what each step printed is in ~/.local/state/atlas-setup/<workspace>.log.
# ---------------------------------------------------------------------------
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="${XDG_STATE_HOME:-$HOME/.local/state}/atlas-setup"
mkdir -p "$LOGS"

# launchd and a bare ssh hand over a short PATH; the tools live in these.
for d in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin" "$HOME/.local/go/bin" "$HOME/.elan/bin"; do
  [ -d "$d" ] && case ":$PATH:" in *":$d:"*) ;; *) PATH="$d:$PATH" ;; esac
done
export PATH

SLURM=0
command -v sbatch >/dev/null 2>&1 && SLURM=1
failed=0

line() { printf '%-32s %s\n' "$1" "$2"; }

# ---- 1. system tools --------------------------------------------------------
if [ "$(uname -s)" = Darwin ] && command -v brew >/dev/null 2>&1; then
  if brew bundle install --no-upgrade --file="$ROOT/Brewfile" >"$LOGS/brew.log" 2>&1; then
    line "Brewfile" "ok"
  else
    line "Brewfile" "FAILED -- $LOGS/brew.log"; failed=1
  fi
else
  if ! command -v uv >/dev/null 2>&1; then
    if curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh >"$LOGS/uv.log" 2>&1 \
        && command -v uv >/dev/null 2>&1; then
      line "uv" "installed in ~/.local/bin"
    else
      line "uv" "FAILED -- $LOGS/uv.log"; failed=1
    fi
  fi
  if ! command -v go >/dev/null 2>&1; then
    case "$(uname -m)" in x86_64) goarch=amd64 ;; aarch64|arm64) goarch=arm64 ;; *) goarch="" ;; esac
    gover="$(curl -fsS 'https://go.dev/dl/?mode=json' 2>>"$LOGS/go.log" \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["version"])' 2>>"$LOGS/go.log")"
    if [ -n "$goarch" ] && [ -n "$gover" ] \
        && curl -fsSL "https://go.dev/dl/$gover.linux-$goarch.tar.gz" -o "$LOGS/go.tar.gz" 2>>"$LOGS/go.log" \
        && rm -rf "$HOME/.local/go" && mkdir -p "$HOME/.local/bin" \
        && tar -C "$HOME/.local" -xzf "$LOGS/go.tar.gz" 2>>"$LOGS/go.log" \
        && ln -sf "$HOME/.local/go/bin/go" "$HOME/.local/go/bin/gofmt" "$HOME/.local/bin/" \
        && PATH="$HOME/.local/go/bin:$PATH" && export PATH \
        && command -v go >/dev/null 2>&1; then
      rm -f "$LOGS/go.tar.gz"
      line "go" "installed $gover in ~/.local/go"
    else
      line "go" "FAILED -- $LOGS/go.log"; failed=1
    fi
  fi
fi

# ---- 2. the workspaces -----------------------------------------------------
# ai-config is the one private repository nested inside Atlas; a machine that
# never cloned it is told the command that brings it in.
if [ ! -e "$ROOT/ai-config/.git" ]; then
  line "ai-config" "not cloned -- bash board/bootstrap.sh"; failed=1
fi

workspaces="$(cd "$ROOT/board" && TUTORBOARD_COURSES="$ROOT" python3 -c '
from tutorboard import subjects
for w in subjects.all():
    print(w["id"])
')" || { line "workspaces" "FAILED -- board/tutorboard/subjects.py did not answer"; exit 1; }

# Does this pyproject.toml declare the optional extra named $2?
has_extra() {
  awk -v want="$2" '
    /^\[/ { inside = ($0 == "[project.optional-dependencies]") ; next }
    inside && $1 == want && $2 == "=" { found = 1 }
    END { exit !found }' "$1"
}

for id in $workspaces; do
  ws="$ROOT/$id"
  log="$LOGS/${id//\//_}.log"
  : >"$log"
  did=""
  bad=0

  if [ -f "$ws/pyproject.toml" ]; then
    extras=()
    has_extra "$ws/pyproject.toml" test && extras+=(--extra test)
    [ "$SLURM" = 1 ] && has_extra "$ws/pyproject.toml" cluster && extras+=(--extra cluster)
    if (cd "$ws" && uv sync --locked ${extras[@]+"${extras[@]}"}) >>"$log" 2>&1; then
      did="uv sync${extras[*]:+ ${extras[*]}}"
    else
      did="uv sync"; bad=1
    fi
  fi

  if [ -f "$ws/lean-toolchain" ]; then
    if [ -f "$ws/scripts/setup.sh" ]; then
      bash "$ws/scripts/setup.sh" >>"$log" 2>&1 || bad=1
    else
      (cd "$ws" && lake exe cache get && lake build) >>"$log" 2>&1 || bad=1
    fi
    did="${did:+$did, }lean"
  fi

  if [ -f "$ws/go.mod" ]; then
    (cd "$ws" && go mod download) >>"$log" 2>&1 || bad=1
    did="${did:+$did, }go mod download"
  fi

  if [ -z "$did" ]; then
    line "$id" "nothing to build"
  elif [ "$bad" = 0 ]; then
    line "$id" "ok ($did)"
  else
    line "$id" "FAILED ($did) -- $log"; failed=1
  fi
done

exit "$failed"
