#!/bin/bash
#SBATCH --job-name=export_paper_figures
#SBATCH --partition=c3_short
#SBATCH --time=00:10:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH -o slurm_jobs/quick_runs/logs/export_paper_figures_%j_out.txt
#SBATCH -e slurm_jobs/quick_runs/logs/export_paper_figures_%j_err.txt

# Paper 1's packet figures that no sweep re-renders, made exportable. It renders
# nothing and reads no row. It checks that each figure below exists under results/
# and is at most 5 MB, the relay's export cap, and prints RELAY: counts plus the
# path of any figure missing or over the cap. It is filed with one --export per
# figure, so the relay copies each into exports/results/ for the Mac.
#
# The five notebook figures live in notebooks/figures/, outside results/, where the
# relay cannot export them. They are copied to results/notebook_figures/ under the
# same name, and the supplement links that copy. The copy is all this recipe writes.
#
# Every figure listed is a plot of aggregate numbers (curves, forest plots,
# histograms over thousands of patients, 2x2 counts) and is already embedded in the
# tracked manuscript.pdf or supplement.pdf.

set -e
source "${SLURM_SUBMIT_DIR:-$PWD}/slurm_jobs/lib/relay_trap.sh"
cd "${SLURM_SUBMIT_DIR:-$PWD}"

CAP=$((5 * 1024 * 1024))

NOTEBOOK_FIGURES="
bge_small_recurrence_bimodality.png
bge_small_cluster0_subsplit.png
density_pre_anchor_history_days.png
density_mdd_to_anchor_days.png
density_num_encounters.png
"

FIGURES="
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/time_zero_timeline.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/discrimination_forest_EMBEDDED_vs_FEATURE.png
results/cross_embedder_robustness_EMBEDDED.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_cumulative_EMBEDDED.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_correlation_cumulative_EMBEDDED.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_logistic_regression_EMBEDDED.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_random_forest_EMBEDDED.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_gradient_boosting_EMBEDDED.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_xgboost_EMBEDDED.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/pr_curves/pr_curve_logistic_regression_EMBEDDED.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/pr_curves/pr_curve_xgboost_FEATURE.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/pr_curve_NEAREST_IMPORTANCE_WEIGHTED_alpha1_k295.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/pr_curve_NEAREST_PLAIN_COSINE_alpha1_k757.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/pr_curve_RANDOM_UNIFORM_k32720.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/calibration_curves/calibration_curve_logistic_regression_EMBEDDED.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/calibration_curves/calibration_curve_xgboost_FEATURE.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/calibration_curve_NEAREST_IMPORTANCE_WEIGHTED_alpha1_k295.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/calibration_curve_NEAREST_PLAIN_COSINE_alpha1_k757.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/calibration_curve_RANDOM_UNIFORM_k32720.png
results/bge-small-en-v1.5/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png
results/bge-en-icl/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png
results/Qwen-Qwen3-Embedding-4B/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png
results/review/metric_intervals/trd_rate_by_prescription_timing.png
results/review/subgroups/subgroup_forest.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_logistic_regression_EMBEDDED.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_xgboost_FEATURE.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/confusion_matrices/confusion_matrix_logistic_regression_EMBEDDED.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/confusion_matrices/confusion_matrix_xgboost_FEATURE.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_logistic_regression.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_random_forest.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_gradient_boosting.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_xgboost.png
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/ablation_roc_ci_EMBEDDED.png
results/notebook_figures/bge_small_recurrence_bimodality.png
results/notebook_figures/bge_small_cluster0_subsplit.png
results/notebook_figures/density_pre_anchor_history_days.png
results/notebook_figures/density_mdd_to_anchor_days.png
results/notebook_figures/density_num_encounters.png
"

copied=0; listed=0
for name in ${NOTEBOOK_FIGURES}; do
  listed=$((listed + 1))
  if [[ -f "notebooks/figures/${name}" ]]; then
    mkdir -p results/notebook_figures
    cp -p "notebooks/figures/${name}" "results/notebook_figures/${name}"
    copied=$((copied + 1))
  fi
done

total=0; present=0; missing=0; oversize=0
for p in ${FIGURES}; do
  total=$((total + 1))
  if [[ ! -f "${p}" ]]; then
    missing=$((missing + 1))
    echo "RELAY: missing ${p}"
  elif (( $(wc -c < "${p}") > CAP )); then
    oversize=$((oversize + 1))
    echo "RELAY: over 5 MB ${p}"
  else
    present=$((present + 1))
  fi
done

echo "RELAY: notebook figures copied ${copied} of ${listed}"
echo "RELAY: figures ${total}, present ${present}, missing ${missing}, over 5 MB ${oversize}"
