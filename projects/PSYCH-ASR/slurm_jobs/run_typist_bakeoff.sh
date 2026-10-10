#!/bin/bash
# ---------------------------------------------------------------------------
# Submit the whole TYPIST bake-off as one dependency chain.
#
#     large-v3        1a-i transcribe (asr_env)  --> 1a-ii align (asr_env) --+
#     large-v3-turbo  1a-i transcribe (asr_env)  --> 1a-ii align (asr_env) --+
#     parakeet        1a-i transcribe (nemo_env) --> 1a-ii align (asr_env) --+--> 1c join
#     canary          1a-i transcribe (nemo_env) --> 1a-ii align (asr_env) --+     (CPU)
#
#     ./slurm_jobs/run_typist_bakeoff.sh
#     ./slurm_jobs/run_typist_bakeoff.sh --stopwatch wav2vec2-large
#     ./slurm_jobs/run_typist_bakeoff.sh --typist parakeet --typist canary
#
# ONE COLUMN MOVES. The stopwatch and the name-tagger are held fixed across the four
# arms, so every difference in the grid's word columns is the typist and nothing else.
# Varying all three at once is step 3's job, and it assembles its cells from runs like
# this one rather than from a nested loop.
#
# THE DEPENDENCY KINDS ARE NOT INTERCHANGEABLE. Each align depends on its own transcribe
# with afterok -- there are no words to time if the typist crashed. The join job depends on
# every align with AFTERANY, so one typist failing still joins the others; a dead typist
# then shows up as a missing cell artifact, which is a result rather than a silent gap.
#
# EACH JOB GETS ITS OWN LOG. The two 1a .sbatch files name a fixed log path, which is
# correct when one typist runs and destroys three of four logs when the bake-off does --
# so the log paths are overridden here, per typist.
#
# Run FROM THE REPO ROOT, having sourced slurm_jobs/lib/job_env.sh -- that is what sets
# PSYCH_ASR_DATA, and this script refuses rather than guessing. Requires exactly one .wav in
# $PSYCH_ASR_DATA/inbox, and the chosen name-tagger's RTTM already in stage1/ from the
# diarizer bake-off.
# ---------------------------------------------------------------------------

set -o errexit
set -o nounset
set -o pipefail

TYPISTS=()
STOPWATCH=wav2vec2-base
NAME_TAGGER=community-1

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --typist)      TYPISTS+=("$2"); shift 2 ;;
        --stopwatch)   STOPWATCH="$2";  shift 2 ;;
        --name-tagger) NAME_TAGGER="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,31p' "$0"
            exit 0 ;;
        *)
            echo "Unknown argument '$1'. See --help." >&2
            exit 1 ;;
    esac
done

# Default to all four, cheapest first, which is the order the plan lists them in.
if [[ "${#TYPISTS[@]}" -eq 0 ]]; then
    TYPISTS=(large-v3 large-v3-turbo parakeet canary)
fi

if [[ ! -d slurm_jobs || ! -d psych_asr ]]; then
    echo "Run this from the repo root -- every job's paths are relative to the submit directory." >&2
    exit 1
fi

# NO FALLBACK. A default address for the session data is worse than none: when it goes stale
# this script looks in a directory that does not exist, finds no .wav, and reports "data/inbox
# must hold exactly 1 .wav file" about the wrong folder entirely -- turning "you did not set
# the variable" into "your data is missing". run_bakeoff.sh beside this one refuses the same
# way.
WAVS=( "${PSYCH_ASR_DATA:?source slurm_jobs/lib/job_env.sh first}"/inbox/*.wav )
if [[ ! -e "${WAVS[0]}" || "${#WAVS[@]}" -ne 1 ]]; then
    echo "data/inbox must hold exactly 1 .wav file (found $([[ -e "${WAVS[0]}" ]] && echo "${#WAVS[@]}" || echo 0))." >&2
    exit 1
fi
STEM=$(basename "${WAVS[0]}" .wav)
TURN_TABLE="${PSYCH_ASR_DATA}/stage1/${STEM}.${NAME_TAGGER}.rttm"
if [[ ! -f "${TURN_TABLE}" ]]; then
    echo "No ${TURN_TABLE}: the grading job would wait for four GPU jobs and then have "\
         "nothing to join onto. Run Stage 1b for ${NAME_TAGGER} first, or name an arm "\
         "that has already run with --name-tagger." >&2
    exit 1
fi

echo "Input      : ${WAVS[0]}"
echo "Stopwatch  : ${STOPWATCH} (held fixed)"
echo "Name-tagger: ${NAME_TAGGER} (held fixed), from ${TURN_TABLE}"
echo ""

mkdir -p slurm_jobs/logs

# The typist registry is stdlib-only at import precisely so an unknown name is refused
# here, on the login node, instead of after a GPU has been allocated and a model loaded.
python -c "
import sys
from psych_asr.asr import typists
unknown = [name for name in sys.argv[1:] if name not in typists.TYPISTS]
if unknown:
    sys.exit(f\"Unknown typist(s) {unknown}; known: {sorted(typists.TYPISTS)}\")
" "${TYPISTS[@]}"

ALIGN_JOBS=()
for TYPIST in "${TYPISTS[@]}"; do
    TRANSCRIBE_JOB=$(sbatch --parsable \
        -o "slurm_jobs/logs/stage1a_transcribe_${TYPIST}_out.txt" \
        -e "slurm_jobs/logs/stage1a_transcribe_${TYPIST}_err.txt" \
        slurm_jobs/stage1a_transcribe.sbatch "${TYPIST}")
    printf '%-34s: %s\n' "1a-i transcribe ${TYPIST}" "${TRANSCRIBE_JOB}"

    ALIGN_JOB=$(sbatch --parsable --dependency=afterok:"${TRANSCRIBE_JOB}" \
        -o "slurm_jobs/logs/stage1a_align_${TYPIST}_out.txt" \
        -e "slurm_jobs/logs/stage1a_align_${TYPIST}_err.txt" \
        slurm_jobs/stage1a_align.sbatch "${TYPIST}" "${STOPWATCH}")
    ALIGN_JOBS+=("${ALIGN_JOB}")
    printf '%-34s: %s\n' "1a-ii align ${TYPIST}" "${ALIGN_JOB}"
done

DEPENDENCY=$(IFS=:; echo "${ALIGN_JOBS[*]}")
JOIN_JOB=$(sbatch --parsable --dependency=afterany:"${DEPENDENCY}" \
    slurm_jobs/stage1c_join_cells.sbatch "${NAME_TAGGER}" "${STOPWATCH}")
printf '%-34s: %s\n' "1c join cells" "${JOIN_JOB}"

echo ""
echo "Watch with: squeue -u \$USER"
echo "Each cell's artifacts land in data/stage1, named"
echo "<stem>.<typist>+<stopwatch>+<name-tagger>. The join log is"
echo "slurm_jobs/logs/stage1c_join_cells_out.txt."
