#!/bin/bash
# coli_ab.sh — run ONE colibri configuration under FLEET-BUILD.md §10's snapshot protocol.
#
#   coli_ab.sh <tag> <extra env assignments...> -- <extra coli args...>
#
# The protocol exists because .coli_usage is a persistent learned routing profile:
# an identical configuration measured 5.46 then 2.56 tok/s with nothing changed.
# So: snapshot the file, let VRAM drain, restore it byte-for-byte, then measure.
set -uo pipefail

TAG=$1; shift
ENVS=(); ARGS=()
while [ $# -gt 0 ]; do
  [ "$1" = "--" ] && { shift; ARGS=("$@"); break; }
  ENVS+=("$1"); shift
done

: "${MODEL:?MODEL must be set}"
: "${COLI_DIR:?COLI_DIR must be set}"
: "${OUTDIR:?OUTDIR must be set}"

USAGE="$MODEL/.coli_usage"
SNAP="$OUTDIR/.coli_usage.snapshot"
LOG="$OUTDIR/cfg_${TAG}.log"

# 1. snapshot the learned profile (first run may have none yet)
if [ -f "$USAGE" ]; then cp -p "$USAGE" "$SNAP"; fi

# 2. VRAM is not released the instant the process exits
sleep 35

# 3. restore byte-for-byte, so every configuration starts from the same profile
if [ -f "$SNAP" ]; then cp -p "$SNAP" "$USAGE"; fi

echo "=== cfg $TAG === $(date -Is)" | tee -a "$OUTDIR/timeline.txt"
echo "    env : ${ENVS[*]:-none}"                | tee -a "$OUTDIR/timeline.txt"
echo "    args: ${ARGS[*]:-none}"                | tee -a "$OUTDIR/timeline.txt"
echo "    wrap: ${WRAP:-none}"                   | tee -a "$OUTDIR/timeline.txt"

T0=$(date +%s.%N)
# WRAP lets a configuration run under numactl without pretending numactl is an env var
read -r -a WRAPA <<< "${WRAP:-}"
env "${ENVS[@]}" "${WRAPA[@]}" python3 "$COLI_DIR/coli" run \
    --model "$MODEL" --ngen "${NGEN:-64}" --ctx "${CTX:-32768}" \
    "${ARGS[@]}" "${PROMPT:-Summarise what a Slurm job dependency does, in three sentences.}" \
    > "$LOG" 2>&1
RC=$?
T1=$(date +%s.%N)
WALL=$(awk "BEGIN{printf \"%.1f\", $T1-$T0}")

# the two lines colibri prints that carry the numbers (colibri.c:8182, :11399)
DEC=$(grep -oE "decode [0-9]+ tokens in [0-9.]+s \([0-9.]+ tok/s\)" "$LOG" | tail -1)
HIT=$(grep -oE "Expert cache hit rate: [0-9.]+%.*" "$LOG" | tail -1)
TPS=$(echo "$DEC" | grep -oE "[0-9.]+ tok/s" | tail -1)

printf 'RESULT tag=%s rc=%s wall_s=%s tps=%s\n' "$TAG" "$RC" "$WALL" "${TPS:-NA}" \
  | tee -a "$OUTDIR/timeline.txt"
[ -n "$DEC" ] && echo "    $DEC" | tee -a "$OUTDIR/timeline.txt"
[ -n "$HIT" ] && echo "    $HIT" | tee -a "$OUTDIR/timeline.txt"
[ $RC -ne 0 ] && { echo "    --- last 20 lines of $LOG ---"; tail -20 "$LOG"; } | tee -a "$OUTDIR/timeline.txt"

# leave the snapshot in place for the next configuration
exit 0
