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
# run the regression gate. The bake-off path; the grid's join is stage1c_join_grid.sbatch.
#
# NO GPU. This step loads no models -- it is a timestamp join and a text render, seconds of
# CPU per arm -- so it asks for no --gres and runs on c3_short rather than occupying the
# single c3_accel node the arms themselves need.
#
# It walks whatever RTTMs exist for this session rather than a fixed arm list, and it does
# not stop when one is missing. That is deliberate: the driver makes this job depend on the
# 1b jobs with afterany, so one arm crashing still lets every other arm produce its
# transcript. A missing arm shows up as a missing file, which is a visible result rather
# than a silent one.
#
# The aligned transcript and the fixture are named exactly from the stem; the arms are every
# <stem>.<arm>.rttm present.
#
# Submit FROM THE REPO ROOT.

set -e
source slurm_jobs/lib/job_env.sh

# INPUT_DIR and STAGE1_DIR come from job_env.sh: the session audio lives OUTSIDE this
# repository, at $PSYCH_ASR_DATA (default: this workspace's `phi/`).

activate_env asr_env

STEM="$(session_stem "${INPUT_DIR}")"

# $1 names which cell's aligned transcript every arm is joined onto. Absent, it is the
# un-armed <stem>.aligned.json that stage1a_asr.sbatch writes.
ALIGNED_PATH="${1:-}"
if [[ -z "${ALIGNED_PATH}" ]]; then
    ALIGNED_PATH="${STAGE1_DIR}/${STEM}.aligned.json"
    if [[ ! -f "${ALIGNED_PATH}" ]]; then
        echo "No un-armed aligned transcript for this session in the Stage 1 directory. Did stage1a_asr run?" >&2
        exit 1
    fi
elif [[ ! -f "${ALIGNED_PATH}" ]]; then
    echo "No such aligned transcript: ${ALIGNED_PATH}" >&2
    exit 1
fi
echo "Session           : ${STEM}"
echo "Aligned transcript: ${ALIGNED_PATH}"

JOINED=0
FAILED=0
for TURN_TABLE in "${STAGE1_DIR}/${STEM}".*.rttm; do
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
# single-job fixture from job 2032471. The fixture is <stem>.diarized.json, with NO arm in
# its name, which is what the single-job path writes and the split never does. Reported,
# never silently skipped -- if the fixture is absent that is itself worth saying out loud.
FIXTURE=""
if [[ -f "${STAGE1_DIR}/${STEM}.diarized.json" ]]; then
    FIXTURE="${STAGE1_DIR}/${STEM}.diarized.json"
fi
CANDIDATE=""
if [[ -f "${STAGE1_DIR}/${STEM}.community-1.diarized.json" ]]; then
    CANDIDATE="${STAGE1_DIR}/${STEM}.community-1.diarized.json"
fi
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
