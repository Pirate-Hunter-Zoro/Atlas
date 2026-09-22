#!/bin/bash
#SBATCH --job-name=stage1c_join
#SBATCH --partition=c3_short
#SBATCH --time=0-00:30:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -o slurm_jobs/logs/stage1c_join_out.txt
#SBATCH -e slurm_jobs/logs/stage1c_join_err.txt

# Stage 1c: join every arm's RTTM onto the shared aligned transcript, render each, then
# run the regression gate.
#
# NO GPU. This step loads no models -- it is a timestamp join and a text render, seconds of
# CPU per arm -- so it asks for no --gres and runs on c3_short rather than occupying the
# single c3_accel node the arms themselves need.
#
# It walks whatever RTTMs exist rather than a fixed arm list, and it does not stop when one
# is missing. That is deliberate: the driver makes this job depend on the 1b jobs with
# afterany, so one arm crashing still lets every other arm produce its transcript. A missing
# arm shows up as a missing file, which is a visible result rather than a silent one.
#
# Submit FROM THE REPO ROOT.

set -e
source slurm_jobs/lib/job_env.sh

STAGE1_DIR=data/stage1
# INPUT_DIR comes from job_env.sh: the session audio lives OUTSIDE this
# repository, at $PSYCH_ASR_DATA (default: this workspace's `phi/`).

activate_env asr_env

# $1 names which cell's aligned transcript every arm is joined onto. It was optional when
# Stage 1a ran once and there was only one; the typist bake-off writes one per cell, and
# then globbing for a sole file finds several and stops. Absent, the old behaviour stands.
ALIGNED_PATH="${1:-}"
if [[ -z "${ALIGNED_PATH}" ]]; then
    ALIGNED_PATH="$(sole_aligned "${STAGE1_DIR}")"
elif [[ ! -f "${ALIGNED_PATH}" ]]; then
    echo "No such aligned transcript: ${ALIGNED_PATH}" >&2
    exit 1
fi
STEM="$(session_stem "${INPUT_DIR}")"
echo "Session           : ${STEM}"
echo "Aligned transcript: ${ALIGNED_PATH}"

JOINED=0
FAILED=0
for TURN_TABLE in "${STAGE1_DIR}"/*.rttm; do
    [[ -e "${TURN_TABLE}" ]] || continue
    # The .exclusive.rttm is community-1's overlap-free view, kept for Stage 3a's overlap
    # features. It is a diagnostic on an existing arm, not an arm of its own.
    case "${TURN_TABLE}" in
        *.exclusive.rttm) echo "Skipping ${TURN_TABLE} (overlap-free view, not an arm)"; continue ;;
    esac

    echo ""
    echo "########## joining ${TURN_TABLE} ##########"
    if python -m psych_asr.cli.join_speakers "${ALIGNED_PATH}" "${TURN_TABLE}"; then
        JOINED=$((JOINED + 1))
    else
        echo "JOIN FAILED for ${TURN_TABLE}"
        FAILED=$((FAILED + 1))
    fi
done

echo ""
echo "Joined ${JOINED} arm(s); ${FAILED} failed."

# The regression gate: the baseline arm composed through the split must reproduce the
# single-job fixture from job 2032471. The fixture is the one .diarized.json with NO arm in
# its name, which is what the single-job path writes and the split never does. Reported,
# never silently skipped -- if the fixture is absent that is itself worth saying out loud.
FIXTURE=$(ls "${STAGE1_DIR}"/*.diarized.json 2>/dev/null | grep -v '\.[a-z0-9-]*\.diarized\.json$' | head -1 || true)
CANDIDATE=$(ls "${STAGE1_DIR}"/*.community-1.diarized.json 2>/dev/null | head -1 || true)
if [[ -n "${FIXTURE}" && -n "${CANDIDATE}" ]]; then
    echo ""
    python -m psych_asr.cli.check_split_regression "${FIXTURE}" "${CANDIDATE}"
else
    echo ""
    echo "Regression check SKIPPED: fixture='${FIXTURE}' candidate='${CANDIDATE}'"
fi

if [[ "${FAILED}" -ne 0 ]]; then
    exit 1
fi
