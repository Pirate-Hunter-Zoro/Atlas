#!/bin/bash
#SBATCH --job-name=stage1c_join_and_grade
#SBATCH --partition=c3_short
#SBATCH --time=0-00:30:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -o slurm_jobs/logs/stage1c_join_and_grade_out.txt
#SBATCH -e slurm_jobs/logs/stage1c_join_and_grade_err.txt

# The typist bake-off's last two steps, in one CPU job: join every typist's aligned
# transcript onto ONE name-tagger's turn table, then grade every cell that exists.
#
#     sbatch slurm_jobs/stage1c_join_and_grade.sbatch                        # community-1
#     sbatch slurm_jobs/stage1c_join_and_grade.sbatch sortformer wav2vec2-base
#
# WHY ONE NAME-TAGGER AND NOT FIVE. Five of the six error labels -- Omission, Insertion,
# Substitution, Proper Noun, Punctuation -- are a property of the TYPIST alone: the words
# come from the typist and the name-tagger reads no words. Varying the diarizer here would
# reproduce the same word-level numbers four more times. The name-tagger is held at the
# incumbent so the WER column moves with exactly one thing.
#
# WHY THE CELL NAME IS A TRIPLE. join_speakers derives the arm from the RTTM's filename,
# which names the name-tagger only. --arm is passed explicitly so the output is
# "<typist>+<stopwatch>+<name-tagger>" and the grid table says which cell each row is.
#
# NO GPU: a timestamp join and a stdlib grader, seconds per cell.
#
# Submit FROM THE REPO ROOT.

set -e
source slurm_jobs/lib/job_env.sh

STAGE1_DIR=data/stage1
# INPUT_DIR comes from job_env.sh: the session audio lives OUTSIDE this
# repository, at $PSYCH_ASR_DATA (default ~/phi/PSYCH-ASR).
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

# A cell joined before --stem was passed to join_speakers is named with its own arm TWICE:
# "<stem>.<typist>+<stopwatch>.<typist>+<stopwatch>+<name-tagger>.diarized.json". The
# grader discovers by glob, so one left behind enrols itself as a duplicate row in the grid
# table. The pattern below matches only that shape -- a correct cell has no dot after the
# stopwatch -- so nothing else in the directory can be caught by it.
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
    echo "Nothing to grade: no ${STEM}.*+${STOPWATCH}.aligned.json in ${STAGE1_DIR}." >&2
    exit 1
fi

# --stem is not optional once the grid runs: find_sole_stem() globs *.aligned.json and a
# dotted arm is indistinguishable from a dotted stem, so discovery finds several and stops.
echo ""
python -m psych_asr.cli.grade_arms --stem "${STEM}"

if [[ "${FAILED}" -ne 0 ]]; then
    exit 1
fi
