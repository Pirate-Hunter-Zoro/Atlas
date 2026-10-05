#!/bin/bash
# Paper 1, thread knn-across-embedders: the cluster work behind manuscript Figures 4-6
# and supplement Figures S8-S9. Prepared, not filed. Run one stage at a time, from the
# Atlas checkout on the Mac, after this branch is merged and pushed:
#
#   bash file-paper1-jobs.sh 0   owner only: mark the 23 figure PNGs aggregate, push
#   bash file-paper1-jobs.sh 1   bge-small rerun, the repair of job 2110916
#   bash file-paper1-jobs.sh 2   only after stage 1's report says completed
#   bash file-paper1-jobs.sh 3   only after all four sweeps of stage 1-2 completed
#
# Stage 2 waits for stage 1 because `board job` refuses a plain neighbor_count_sweep
# request on this thread while the 2026-10-02 repair is open; a completed rerun closes
# it. Stage 3 reads all four sweeps. Every --export must be marked aggregate on the
# thread first (stage 0), or `board job` refuses the request whole.
#
# The k in each best_k_panels filename is the k the prose quotes. If a rerun moves an
# encoder's best k, that export is refused as missing and the prose must follow the
# encoder's best_k_panels.json (thread task: check each Figure S8-S9 panel path).
set -euo pipefail

ATLAS="$(cd "$(dirname "$0")" && pwd -P)"
BOARD="${ATLAS}/board/bin/board"
WS="${ATLAS}/research/TRD-EHR"
T=knn-across-embedders
SWEEP=slurm_jobs/quick_runs/neighbor_count_sweep.sbatch
CROSS=slurm_jobs/quick_runs/plot_cross_embedder_retrieval.sbatch
FAILED=2026-10-02-knn-across-embedders-neighbor-count-sweep
JUDGE=google_medgemma-27b-text-it
cd "${WS}"

sweep_dir() { echo "results/$1/${JUDGE}/neighbor_count_sweep"; }

# --produces and --export for one encoder's sweep: its Figure-4-style panel and the
# ROC and confusion panels the supplement links, each "<arm prefix>_k<k>".
encoder_args() {
    local enc="$1"; shift
    local d; d="$(sweep_dir "${enc}")"
    echo "--produces ${d} --produces ${d}/neighbor_count_sweep_manuscript.png"
    echo "--export ${d}/neighbor_count_sweep_manuscript.png"
    local mode kind
    for mode in "$@"; do
        for kind in roc_curve confusion_matrix; do
            echo "--export ${d}/best_k_panels/${kind}_${mode}.png"
        done
    done
}

# The cluster runs what origin holds, so the recipes and the figure code must be
# committed, unchanged, and pushed before anything is filed.
require_pushed() {
    if [[ -n "$(git status --porcelain -- slurm_jobs scripts/pipeline/predictions threads.json)" ]]; then
        echo "refusing: uncommitted edits under slurm_jobs/, scripts/pipeline/predictions/ or threads.json" >&2
        exit 1
    fi
    git fetch --quiet
    if ! git merge-base --is-ancestor HEAD '@{u}'; then
        echo "refusing: HEAD is not pushed; the cluster would run older code" >&2
        exit 1
    fi
}

case "${1:-}" in
0)
    # The owner's word, never a turn's: every PNG below is a plot of aggregate metrics
    # (AUC curves, ROC curves, 2x2 confusion counts, one point per encoder) destined
    # for the public paper. No CSV or JSON is listed.
    if [[ "${OWNER_SAYS_AGGREGATE:-}" != yes ]]; then
        echo "stage 0 is the owner's answer: rerun with OWNER_SAYS_AGGREGATE=yes" >&2
        exit 1
    fi
    python3 -c '
import json, sys
thread = [t for t in json.load(open("threads.json"))["threads"] if t["id"] == sys.argv[1]][0]
for e in thread["exports"]:
    print(e["path"])' "${T}" | while read -r p; do
        "${BOARD}" thread export "${T}" "${p}" --aggregate
    done
    "${BOARD}" push "TRD-EHR: Paper 1 figure exports marked aggregate"
    ;;
1)
    require_pushed
    # Route A. The report names FileNotFoundError and nothing else (it predates the
    # RELAY: trap); plot_neighbor_sweep_figure read test_predictions_*.parquet, which
    # only the primary encoder has, and now reads classical_ml_results_*.json instead.
    # No REDRAW: whether the 10-02 sweep itself finished is unproven.
    # shellcheck disable=SC2046
    "${BOARD}" job "${T}" --fixes "${FAILED}" \
        $(encoder_args bge-small-en-v1.5 \
            NEAREST_IMPORTANCE_WEIGHTED_alpha1_k579 NEAREST_PLAIN_COSINE_alpha1_k1243) \
        -- "${SWEEP}" EMBEDDER=bge-small-en-v1.5
    # Route B, only if the rerun fails without saying why (spends one of 3 attempts):
    #   "${BOARD}" diagnose "${T}" --fixes "${FAILED}" -- slurm_jobs/quick_runs/diagnose.sbatch \
    #       EMBEDDER=bge-small-en-v1.5 LOOK=RESULTS_DIR \
    #       MODULE=scripts.pipeline.predictions.plot_neighbor_sweep_figure
    ;;
2)
    require_pushed
    # shellcheck disable=SC2046
    "${BOARD}" job "${T}" \
        $(encoder_args bge-en-icl \
            NEAREST_IMPORTANCE_WEIGHTED_alpha1_k1519 NEAREST_PLAIN_COSINE_alpha1_k413) \
        -- "${SWEEP}" EMBEDDER=bge-en-icl
    # shellcheck disable=SC2046
    "${BOARD}" job "${T}" \
        $(encoder_args Qwen-Qwen3-Embedding-4B \
            NEAREST_IMPORTANCE_WEIGHTED_alpha1_k684 NEAREST_PLAIN_COSINE_alpha1_k493) \
        -- "${SWEEP}" EMBEDDER=Qwen-Qwen3-Embedding-4B
    # The primary encoder's sweep stands; REDRAW=1 only redraws Figure 4 and its
    # panels so they are exported. Its figure code path is unchanged.
    # shellcheck disable=SC2046
    "${BOARD}" job "${T}" \
        $(encoder_args Qwen-Qwen3-Embedding-8B \
            NEAREST_IMPORTANCE_WEIGHTED_alpha1_k295 NEAREST_PLAIN_COSINE_alpha1_k757 \
            RANDOM_UNIFORM_k32720) \
        -- "${SWEEP}" EMBEDDER=Qwen-Qwen3-Embedding-8B REDRAW=1
    ;;
3)
    require_pushed
    "${BOARD}" job "${T}" \
        --produces results/cross_embedder_retrieval/cross_embedder_retrieval.csv \
        --produces results/cross_embedder_retrieval/lr_dimensions_vs_best_k.png \
        --export results/cross_embedder_retrieval/lr_dimensions_vs_best_k.png \
        -- "${CROSS}"
    ;;
*)
    sed -n '2,19p' "$0"
    exit 2
    ;;
esac
