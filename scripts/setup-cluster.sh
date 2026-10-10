#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup-cluster.sh -- bring the cluster's Atlas checkout fully up to date.
#
#     cd ~/Atlas && bash scripts/setup-cluster.sh
#
# Run it on a compute node (salloc, then ssh to the node): the login node
# forbids running code, and this builds environments. A fresh clone or an old
# checkout, it does the same thing, and a second run changes nothing:
#
#   1  main, fast-forward only
#   2  the relay: bootstrap, ai-config, the scrontab entry, origin
#      (board/scripts/setup-cluster.sh)
#   3  every subject's environment (scripts/setup.sh): uv, Go from conda-forge,
#      elan and the Lean toolchain
#   4  the PHI guards: ai-config's tests, phi-probe, board/test/tracked.py
#   5  the assistant CLIs: ai-config linked, and every CLI its descriptors know
#      how to install, installed when missing (none is required)
#   6  Mathlib, as a Slurm job when it is not built and no build is queued
#   7  the colibri build, reported (it needs CUDA; the README's command)
#   8  one relay pass, and relay/status.json has no error
#
# Nothing here needs a hosted model's login. The CLIs are for the owner's own
# use; the system never calls them here, and logging in is by hand, once.
#
# It never stops at the first problem. Each line says ok or ----, and the last
# line counts what still needs a person. Logs: ~/.local/state/atlas-setup/.
# ---------------------------------------------------------------------------
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="${XDG_STATE_HOME:-$HOME/.local/state}/atlas-setup"
mkdir -p "$LOGS"
cd "$ROOT" || exit 1
for d in "$HOME/.local/bin" "$HOME/.elan/bin"; do
  case ":$PATH:" in *":$d:"*) ;; *) PATH="$d:$PATH" ;; esac
done
export PATH

problems=0
good() { printf '  ok    %s\n' "$*"; }
warn() { printf '  ----  %s\n' "$*"; problems=$((problems + 1)); }

command -v sbatch >/dev/null 2>&1 \
  || { echo "no sbatch: this is not the cluster. On the Mac: bash scripts/setup-mac.sh"; exit 1; }
case "$(hostname -s)" in
  submit*) echo "this is a login node, where running code is forbidden. salloc, ssh to the node, rerun."; exit 1 ;;
esac

echo "== 1. main"
if GIT_TERMINAL_PROMPT=0 git pull -q --ff-only origin main 2>"$LOGS/pull.log"; then
  good "main at $(git log -1 --oneline)"
else
  warn "git pull --ff-only refused (local commits or edits); see $LOGS/pull.log and git status"
fi

echo "== 2. the relay"
bash board/scripts/setup-cluster.sh 2>&1 | sed 's/^/  /'
[ "${PIPESTATUS[0]}" -eq 0 ] || problems=$((problems + 1))

echo "== 3. environments"
bash scripts/setup.sh 2>&1 | tee "$LOGS/setup.log" | sed 's/^/  /'
[ "${PIPESTATUS[0]}" -eq 0 ] || warn "scripts/setup.sh: a FAILED line above names its log"

echo "== 4. the PHI guards"
if [ -e ai-config/.git ]; then
  bash ai-config/scripts/test.sh >"$LOGS/ai-config-test.log" 2>&1 \
    && good "ai-config's tests pass" || warn "ai-config's tests fail; see $LOGS/ai-config-test.log"
fi
bash board/scripts/phi-probe.sh projects/PSYCH-ASR/phi/x >/dev/null 2>&1 \
  && good "phi-probe refuses projects/PSYCH-ASR/phi/x" || warn "phi-probe does not refuse projects/PSYCH-ASR/phi/x"
python3 board/test/tracked.py >"$LOGS/tracked.log" 2>&1 \
  && good "tracked.py: git can see nothing it must not" || warn "tracked.py fails; see $LOGS/tracked.log"

echo "== 5. assistant CLIs"
# None is load-bearing: a CLI that will not install is reported, never a stop.
# ai-config links each one's contract, PHI hook and settings and the shell
# block; install-clis puts in any its descriptors know how to install.
if [ -f ai-config/scripts/install.sh ]; then
  # ai-config is its own repository and Atlas's pull never moves it.
  GIT_TERMINAL_PROMPT=0 git -C ai-config pull -q --ff-only origin main 2>"$LOGS/ai-config-pull.log" \
    && good "ai-config at $(git -C ai-config log -1 --format=%h)" \
    || warn "ai-config would not fast-forward (local commits or edits); see $LOGS/ai-config-pull.log"
  bash ai-config/scripts/install.sh >"$LOGS/ai-config-install.log" 2>&1 \
    && good "ai-config linked (contract, PHI hook, settings, shell)" \
    || warn "ai-config's install.sh failed; see $LOGS/ai-config-install.log"
  bash ai-config/scripts/install-clis.sh 2>&1 | sed 's/^/  /'
  [ "${PIPESTATUS[0]}" -eq 0 ] || warn "an assistant CLI did not install; the line above says how by hand"
else
  warn "no ai-config here; bootstrap clones it, then rerun"
fi

echo "== 6. Mathlib"
LEAN="$ROOT/projects/Lean-Theorem-Proving"
if [ ! -f "$LEAN/lean-toolchain" ]; then
  good "no Lean project here"
elif [ -n "$(find "$LEAN/.lake/packages/mathlib/.lake/build" -name Mathlib.olean -print -quit 2>/dev/null)" ]; then
  good "Mathlib is built"
elif [ -n "$(squeue -u "$USER" -h -n mathlib -o %i 2>/dev/null)" ]; then
  good "a Mathlib build is already queued or running (squeue -n mathlib)"
elif job="$(cd "$LEAN" && sbatch --parsable slurm_jobs/build_mathlib.sbatch 2>"$LOGS/mathlib-sbatch.log")"; then
  good "Mathlib build submitted as job $job; progress in $LEAN/slurm_jobs/build_mathlib_out.txt"
else
  warn "sbatch of the Mathlib build failed; see $LOGS/mathlib-sbatch.log"
fi

echo "== 7. colibri"
if [ -x vendor/colibri-build/c/colibri ]; then
  good "vendor/colibri-build/c/colibri is built"
else
  warn "vendor/colibri-build is not built; projects/libr-local-llm/README.md has the make line (CUDA, GCC modules)"
fi

echo "== 8. one relay pass"
if bash board/scripts/relay-pass.sh >"$LOGS/relay-pass.log" 2>&1; then
  err="$(python3 -c 'import json; print(json.load(open("relay/status.json")).get("last_error") or "")' 2>/dev/null)"
  if [ -n "$err" ]; then warn "relay/status.json last_error: $err"; else good "relay pass ran; relay/status.json has no error"; fi
else
  warn "the relay pass failed; see $LOGS/relay-pass.log"
fi

echo
if [ "$problems" -eq 0 ]; then
  echo "THE CLUSTER IS UP TO DATE."
else
  echo "$problems thing(s) above still need a person."
fi
exit "$problems"
