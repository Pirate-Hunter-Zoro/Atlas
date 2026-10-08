import os
import numpy as np
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

from scripts.pipeline.neighbors.retriever import Retriever
from scripts.pipeline.neighbors.neighbor_scheme import NeighborScheme
from scripts.shared.utils import load_neighborhood_data

from dotenv import load_dotenv
load_dotenv()

def run_chonology_check():
    """
    Helper function to evaluate TRD prediction performance over varying pre-anchor patient history lengths
    """
    # Load the actual prediction risk scores
    risk_scores_df = pd.read_csv(Path(os.environ['RESULTS_DIR']) / f'summary_predictions.csv')
    
    # Load patient pre-anchor history lengths
    retriever = Retriever()
    lengths_df = pd.DataFrame({
        'id': retriever.ids,
        'chronological_length': retriever.chronological_lengths
    })
    # Merge that into the risk scores dataframe
    risk_scores_df = risk_scores_df.merge(lengths_df, left_on='anchor_patient_id', right_on='id', how='left')
    
    risk_scores_df['prediction_error'] = (risk_scores_df['predicted_risk'] - risk_scores_df['true_label']).abs()
    grouped_risk_scores_df = risk_scores_df.groupby(['weighting_strategy', 'neighbor_scheme']) # Group results by weighting strategy used
    check_results = []
    for (weighting_strat, neighbor_scheme), results in grouped_risk_scores_df:
        chronological_lengths = results['chronological_length']
        prediction_error = results['prediction_error']
        # Find correlation between time length and prediction error
        correlation, p_value = spearmanr(np.array(chronological_lengths), np.array(prediction_error))
        # Create scatter plot
        plt.figure(figsize=(10,6))
        plt.scatter(chronological_lengths, prediction_error)
        plt.xlabel('Pre-Anchor History (Days)')
        plt.ylabel('TRD Probability Prediction Error')
        plt.title(f'Error vs. Pre-Anchor History: {neighbor_scheme}_{weighting_strat}')
        save_path = Path(os.environ['RESULTS_DIR']) / 'chronology_checks' / f'chronology_check_{neighbor_scheme}_{weighting_strat}.png'
        os.makedirs(save_path.parent, exist_ok=True)
        plt.savefig(str(save_path))
        plt.close()
        check_results.append({
            'weighting_strategy': weighting_strat,
            'spearman_rho_correlation': correlation,
            'p_value': p_value,
        })
    pd.DataFrame(check_results).to_csv(Path(os.environ['RESULTS_DIR']) / f'chronology_check.csv')

COSINE_FIGURE_NAME = 'cosine_score_random_vs_neighbor.png'
# Figure S6's panels are placed at 5.8in from a 10in canvas, a 0.58 downscale; these
# sizes print at about 8-9pt there.
COSINE_FONT_SIZES = {"tick": 14, "label": 15, "title": 16, "legend": 14}
COSINE_BINS = 100


def draw_cosine_densities(random_sims: np.ndarray, neighbor_sims: np.ndarray, save_path: Path,
                          title: str = None, n_neighbors: int = None):
    """Figure S6, one panel: random-pair and nearest-neighbor-pair cosine similarity.

    Both are drawn as DENSITIES on one shared set of bins. As raw counts the random pairs
    (every pair of test patients, tens of millions) bury the neighbor pairs (k per
    anchor) under a y-axis in millions, which is the comparison the caption asks for.
    Each distribution is a filled step outline, red for random and green for neighbors,
    as the caption names them.

    Args:
        random_sims (np.ndarray): Cosine similarity of every distinct anchor pair.
        neighbor_sims (np.ndarray): Cosine similarity of each anchor to its neighbors.
        save_path (Path): Destination PNG.
        title (str, optional): Axes title, e.g. the encoder's name.
        n_neighbors (int, optional): Neighbors per anchor, for the legend.

    Returns:
        tuple: (figure, axis), already saved and still open, for a caller that checks it.
    """
    low = float(min(np.min(random_sims), np.min(neighbor_sims)))
    high = float(max(np.max(random_sims), np.max(neighbor_sims)))
    bins = np.linspace(low, high, COSINE_BINS + 1)
    neighbor_label = "Nearest-neighbor pairs" + (f" (k = {n_neighbors} per patient)" if n_neighbors else "")
    figure, axis = plt.subplots(figsize=(10, 5.4))
    for values, color, label in ((random_sims, '#d62728', "Random pairs"),
                                 (neighbor_sims, '#2ca02c', neighbor_label)):
        axis.hist(values, bins=bins, density=True, histtype='stepfilled', alpha=0.35, color=color)
        axis.hist(values, bins=bins, density=True, histtype='step', linewidth=1.8, color=color,
                  label=label)
    axis.set_xlabel("Cosine similarity", fontsize=COSINE_FONT_SIZES["label"])
    axis.set_ylabel("Density", fontsize=COSINE_FONT_SIZES["label"])
    if title:
        axis.set_title(title, fontsize=COSINE_FONT_SIZES["title"])
    axis.tick_params(axis='both', labelsize=COSINE_FONT_SIZES["tick"])
    axis.legend(loc='upper left', fontsize=COSINE_FONT_SIZES["legend"], frameon=False)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)
    figure.tight_layout()
    figure.savefig(save_path, dpi=220)
    return figure, axis


def run_cosine_check(title: str = None):
    """Helper function to produce a graph of cosine similarity over random patient pairs versus neighbor patient pairs

    Args:
        title (str, optional): Axes title, e.g. the encoder's display name.
    """
    # Load anchor patient neighborhood data frame
    df = load_neighborhood_data()
    df = df[df['neighbor_scheme'] == NeighborScheme.NEAREST.name]

    # Compute anchor to anchor similarities. No history histogram: this check is redrawn
    # on its own, and must not rewrite a figure it was not asked for.
    retriever = Retriever(save_time_hist=False)
    unique_anchor_ids = df['anchor_patient_id'].unique()
    anchor_indices = np.array([retriever.ids_to_index[id] for id in unique_anchor_ids])
    anchor_vectors = retriever.vectors[anchor_indices]
    sim_matrix = np.dot(anchor_vectors, anchor_vectors.T) # (N x k) x (k x N) -> (N x N) similarities
    unique_pair_sims = sim_matrix[np.triu_indices(sim_matrix.shape[0], k=1)] # Exclude self pairs
    per_anchor = df.groupby('anchor_patient_id').size()
    n_neighbors = int(per_anchor.iloc[0]) if per_anchor.nunique() == 1 else None
    figure, _ = draw_cosine_densities(unique_pair_sims, df['cosine_sim'].to_numpy(),
                                      Path(os.environ['RESULTS_DIR']) / COSINE_FIGURE_NAME,
                                      title=title, n_neighbors=n_neighbors)
    plt.close(figure)
    # Counts and the two medians, which the caption's comparison rests on; aggregate only.
    print(f"RELAY: S6 random pairs {unique_pair_sims.size}, neighbor pairs {len(df)}, "
          f"median random {np.median(unique_pair_sims):.3f}, "
          f"median neighbor {np.median(df['cosine_sim']):.3f}", flush=True)
    
def run_trd_sanity_checks():
    run_chonology_check()
    run_cosine_check()


if __name__ == "__main__":
    # `--cosine-only` redraws Figure S6's panel for the encoder .env names, titled with
    # its display name, and nothing else (redraw_cosine_check.sbatch).
    import sys
    if "--cosine-only" in sys.argv[1:]:
        from scripts.shared.display_names import encoder_display
        run_cosine_check(title=encoder_display(os.environ['EMBEDDER_MODEL_NAME']))
    else:
        run_trd_sanity_checks()