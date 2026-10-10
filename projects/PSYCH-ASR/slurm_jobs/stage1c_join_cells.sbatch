#!/bin/bash
#SBATCH --job-name=stage1c_join_cells
#SBATCH --partition=c3_short
#SBATCH --time=0-00:30:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -o slurm_jobs/logs/stage1c_join_cells_out.txt
#SBATCH -e slurm_jobs/logs/stage1c_join_cells_err.txt

# The typist grid's join step: join every typist's aligned transcript onto ONE
# name-tagger's turn table, one output artifact per grid cell.
#
#     sbatch slurm_jobs/stage1c_join_cells.sbatch                        # community-1
#     sbatch slurm_jobs/stage1c_join_cells.sbatch sortformer wav2vec2-base
#
# WHY ONE NAME-TAGGER AND NOT FIVE. The words in a cell come from the TYPIST alone; the
# name-tagger reads no words and only labels them. Varying the diarizer here reproduces the
# same word sequence four more times, so the name-tagger is held at the incumbent and the
# typist is the one thing that moves.
#
# WHY THE CELL NAME IS A TRIPLE. join_speakers derives the arm from the RTTM's filename,
# which names the name-tagger only. --arm is passed explicitly so the output is
# "<typist>+<stopwatch>+<name-tagger>" and the filename says which cell it is.
#
# NO GPU: a timestamp join, seconds per cell.
#
# Submit FROM THE REPO ROOT.

set -e
source slurm_jobs/lib/job_env.sh

STAGE1_DIR=data/stage1
# INPUT_DIR comes from job_env.sh: the session audio lives OUTSIDE this
# repository, at $PSYCH_ASR_DATA (default: this workspace's `phi/`).
NAME_TAGGER="${1:-community-1}"
STOPWATCH="${2:-wav2vec2-base}"

activate_env asr_env

STEM="$(session_stem "${INPUT_DIR}")"
TURN_TABLE="${STAGE1_DIR}/${STEM}.${NAME_TAGGER}.rttm"
if [[ ! -f "${TURN_TABLE}" ]]; then
    echo "No ${TURN_TABLE}. Stage 1b has not run for ${NAME_TAGGER}." >&2
    exit 1
fi

echo "Session    : ${STEM}"
echo "Name-tagger: ${NAME_TAGGER} (held fixed; only the typist varies)"
echo "Stopwatch  : ${STOPWATCH}"

# A cell joined without --stem is named with its own arm TWICE:
# "<stem>.<typist>+<stopwatch>.<typist>+<stopwatch>+<name-tagger>.diarized.json". Arm
# discovery is by glob, so one left behind enrols itself as an extra arm. The pattern below
# matches only that shape -- a correct cell has no dot after the stopwatch -- so nothing
# else in the directory can be caught by it.
for STALE in "${STAGE1_DIR}"/${STEM}.*+${STOPWATCH}.*.diarized.json \
             "${STAGE1_DIR}"/${STEM}.*+${STOPWATCH}.*.transcript.txt; do
    [[ -e "${STALE}" ]] || continue
    echo "Removing doubly-named cell ${STALE}"
    rm -f "${STALE}"
done

JOINED=0
FAILED=0
for ALIGNED in "${STAGE1_DIR}"/${STEM}.*+${STOPWATCH}.aligned.json; do
    [[ -e "${ALIGNED}" ]] || continue
    HALF_CELL="$(basename "${ALIGNED}" .aligned.json)"
    HALF_CELL="${HALF_CELL#"${STEM}."}"
    CELL="${HALF_CELL}+${NAME_TAGGER}"

    echo ""
    echo "########## joining ${CELL} ##########"
    if python -m psych_asr.cli.join_speakers "${ALIGNED}" "${TURN_TABLE}" \
            --stem "${STEM}" --arm "${CELL}"; then
        JOINED=$((JOINED + 1))
    else
        echo "JOIN FAILED for ${CELL}"
        FAILED=$((FAILED + 1))
    fi
done

echo ""
echo "Joined ${JOINED} cell(s); ${FAILED} failed."
if [[ "${JOINED}" -eq 0 ]]; then
    echo "No ${STEM}.*+${STOPWATCH}.aligned.json in ${STAGE1_DIR}; Stage 1a has not run." >&2
    exit 1
fi

if [[ "${FAILED}" -ne 0 ]]; then
    exit 1
fi
