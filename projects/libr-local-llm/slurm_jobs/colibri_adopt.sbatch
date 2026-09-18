#!/bin/bash
# The chain's handover loop, standing beside a generation that has none of its
# own. Submitted by `coli-adopt`, which passes the job and node to watch.
#
# A FILE RATHER THAN `sbatch --wrap`, and the reason is one line of syntax:
# `--wrap` builds a `#!/bin/sh` script, and `scripts/colibri-env.sh` opens with
# `${BASH_SOURCE[0]:-$0}` -- an array subscript, which a POSIX shell refuses at
# PARSE time whether or not that branch would ever run.
#
#SBATCH --job-name=colibri_adopt
#SBATCH --partition=c3_short
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=09:00:00
set -uo pipefail

: "${LLM_REPO:=${SLURM_SUBMIT_DIR:-}}"
if [ -z "$LLM_REPO" ] || [ ! -r "$LLM_REPO/scripts/colibri-env.sh" ]; then
    echo "colibri_adopt: LLM_REPO is not set. Submit with coli-adopt." >&2
    exit 1
fi
. "$LLM_REPO/scripts/colibri-env.sh"

WATCHED="${COLI_ADOPT_JOB:-}"
NODE="${COLI_ADOPT_NODE:-}"
if [ -z "$WATCHED" ] || [ -z "$NODE" ]; then
    echo "colibri_adopt: no generation named. Submit with coli-adopt." >&2
    exit 1
fi

echo "colibri_adopt job=${SLURM_JOB_ID} watching=${WATCHED} on=${NODE} start=$(date -Is)"
coli_chain_watch "$WATCHED" "$NODE"
echo "colibri_adopt done at=$(date -Is)"
