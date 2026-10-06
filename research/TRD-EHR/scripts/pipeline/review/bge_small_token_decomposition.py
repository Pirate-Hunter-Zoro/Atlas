"""Supplement Figure S7: bge-small-en-v1.5 pairwise similarity split by one token.

Usage:
    python -m scripts.pipeline.review.bge_small_token_decomposition

The two panels were drawn in notebooks/cohort_investigation.ipynb (the cells defining
cluster_vectors and plot_pairwise_decomposition). This is that computation as a module,
so the figure can be redrawn by a recipe and titled as the paper names things: the
recurrent cluster is "cluster A", never "Cluster 0".

  A  every pair of patients, split by whether both or neither narrative contains the
     token that best separates a two-cluster KMeans of the whole cohort ("episode"), or
     exactly one does;
  B  the same inside cluster A (KMeans label 0, the recurrent cluster), with the token
     that best separates ITS two sub-clusters ("recurrent").

Grey is all pairs, red pairs that disagree on the token, blue pairs that agree, as the
caption says. KMeans, the vectorizer and the token choice are the notebook's, with the
rows read in the same order, so the clusters are the same clusters.

The notebook held every pair in memory, about 30 GB for 42,579 patients. Here the pairs
are visited one block of rows at a time and only histogram counts are kept, which gives
the same counts on the same bins.

It prints RELAY: lines that say whether the redraw found what the paper describes:
whether each driving token is the expected one (yes or no, never the word itself), the
cluster sizes, and cluster A's nested silhouette. Writes both panels to
results/notebook_figures/ and notebooks/figures/, so the copy export_paper_figures makes
from the second cannot put the old title back.
"""

import os
import sqlite3
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import silhouette_score

from dotenv import load_dotenv
load_dotenv()

ENCODER = "bge-small-en-v1.5"
EXPECTED_DIMENSIONS = 384
EXPECTED_TOKENS = {"cohort": "episode", "cluster_a": "recurrent"}
# KMeans label of cluster A, as the notebook numbered it.
CLUSTER_A_LABEL = 0
BINS = 100
ROW_BLOCK = 1024
OUTPUT_DIRS = (Path("results/notebook_figures"), Path("notebooks/figures"))
FILE_NAMES = {"cohort": "bge_small_recurrence_bimodality.png",
              "cluster_a": "bge_small_cluster0_subsplit.png"}
FONT_SIZES = {"tick": 14, "label": 15, "title": 16, "legend": 14}


def cluster_vectors(vectors: np.ndarray, texts: list[str], seed: int) -> tuple[np.ndarray, str]:
    """Two-cluster KMeans, and the token whose presence differs most between the clusters.

    Args:
        vectors (np.ndarray): L2-normalised embeddings, shape (n, d).
        texts (list[str]): Lower-cased narratives, aligned with vectors.
        seed (int): KMeans random_state.

    Returns:
        tuple[np.ndarray, str]: (cluster label per row, the driving token).
    """
    labels = KMeans(n_clusters=2, random_state=seed, n_init=10).fit_predict(vectors)
    vectorizer = CountVectorizer(binary=True)
    presence = vectorizer.fit_transform(texts)
    vocab = vectorizer.get_feature_names_out()
    share_0 = np.asarray(presence[labels == 0].mean(axis=0)).ravel()
    share_1 = np.asarray(presence[labels == 1].mean(axis=0)).ravel()
    return labels, str(vocab[int(np.argsort(np.abs(share_0 - share_1))[::-1][0])])


def pair_blocks(vectors: np.ndarray, row_block: int = ROW_BLOCK):
    """Yield (row indices, column indices, similarities) for every pair i < j, by row block.

    Args:
        vectors (np.ndarray): L2-normalised rows.
        row_block (int): Rows per block.
    """
    n = vectors.shape[0]
    for start in range(0, n, row_block):
        stop = min(start + row_block, n)
        sims = vectors[start:stop] @ vectors.T
        rows, cols = np.nonzero(np.arange(start, stop)[:, None] < np.arange(n)[None, :])
        yield rows + start, cols, sims[rows, cols]


def decomposition_counts(vectors: np.ndarray, contains: np.ndarray, bins: int = BINS,
                         row_block: int = ROW_BLOCK) -> dict:
    """Histogram counts of all pairs, disagreeing pairs and agreeing pairs on shared bins.

    The bins span the smallest to the largest pair similarity, as the notebook's did.

    Args:
        vectors (np.ndarray): L2-normalised rows.
        contains (np.ndarray): Boolean, whether each row's narrative holds the token.
        bins (int): Bin count.
        row_block (int): Rows per block.

    Returns:
        dict: edges, and counts for "all", "differ" and "same".
    """
    low, high = np.inf, -np.inf
    for _, _, sims in pair_blocks(vectors, row_block):
        if sims.size:
            low, high = min(low, float(sims.min())), max(high, float(sims.max()))
    edges = np.linspace(low, high, bins + 1)
    counts = {name: np.zeros(bins, dtype=np.int64) for name in ("all", "differ", "same")}
    for rows, cols, sims in pair_blocks(vectors, row_block):
        differ = contains[rows] ^ contains[cols]
        counts["all"] += np.histogram(sims, bins=edges)[0]
        counts["differ"] += np.histogram(sims[differ], bins=edges)[0]
        counts["same"] += np.histogram(sims[~differ], bins=edges)[0]
    return {"edges": edges, **counts}


def draw(counts: dict, token: str, title: str, save_paths: list[Path]) -> None:
    """One panel of Figure S7 from decomposition_counts.

    Args:
        counts (dict): decomposition_counts output.
        token (str): The driving token, named in the legend.
        title (str): Axes title.
        save_paths (list[Path]): Every place the PNG is written.
    """
    edges = counts["edges"]
    figure, axis = plt.subplots(figsize=(10, 5.4))
    for name, color, alpha, label in (("all", "gray", 0.3, "all pairs"),
                                      ("differ", "firebrick", 0.5, f"differ on '{token}'"),
                                      ("same", "steelblue", 0.5, f"same on '{token}'")):
        axis.stairs(counts[name], edges, fill=True, color=color, alpha=alpha, label=label)
    axis.set_xlabel("Cosine similarity", fontsize=FONT_SIZES["label"])
    axis.set_ylabel("Pairs", fontsize=FONT_SIZES["label"])
    axis.set_title(title, fontsize=FONT_SIZES["title"])
    axis.tick_params(axis="both", labelsize=FONT_SIZES["tick"])
    axis.legend(fontsize=FONT_SIZES["legend"], frameon=False)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)
    figure.tight_layout()
    for path in save_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def load_bge_small() -> tuple[np.ndarray, list[str]]:
    """Every narrative's bge-small embedding, normalised, and its lower-cased text.

    Rows are read in the table's own order, with no ORDER BY, as the notebook read them,
    so KMeans sees the same sequence.
    """
    if os.environ.get("EMBEDDER_MODEL_NAME") != ENCODER:
        raise ValueError(f"EMBEDDER_MODEL_NAME must be {ENCODER}; the recipe sets it.")
    connection = sqlite3.connect(Path(os.environ["EMBEDDINGS_DIR"]) / "embeddings.db")
    rows = connection.execute("SELECT patient_id, embedding, text FROM embeddings").fetchall()
    connection.close()
    vectors = np.vstack([np.frombuffer(r[1], dtype=np.float32) for r in rows]).astype(np.float32)
    if vectors.shape[1] != EXPECTED_DIMENSIONS:
        raise ValueError(f"Expected {EXPECTED_DIMENSIONS}-dimensional vectors, got {vectors.shape[1]}.")
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True), [r[2].lower() for r in rows]


def main():
    seed = int(os.environ["SEED"])
    vectors, texts = load_bge_small()
    labels, cohort_token = cluster_vectors(vectors, texts, seed)
    cohort_contains = np.array([cohort_token in t for t in texts])
    draw(decomposition_counts(vectors, cohort_contains), cohort_token,
         f"{ENCODER}: all pairs, split by agreement on '{cohort_token}'",
         [d / FILE_NAMES["cohort"] for d in OUTPUT_DIRS])

    in_a = labels == CLUSTER_A_LABEL
    cluster_a = vectors[in_a]
    cluster_a_texts = [t for t, keep in zip(texts, in_a) if keep]
    sub_labels, sub_token = cluster_vectors(cluster_a, cluster_a_texts, seed)
    sub_contains = np.array([sub_token in t for t in cluster_a_texts])
    draw(decomposition_counts(cluster_a, sub_contains), sub_token,
         f"Cluster A: pairs split by agreement on '{sub_token}'",
         [d / FILE_NAMES["cluster_a"] for d in OUTPUT_DIRS])

    silhouette = silhouette_score(cluster_a, sub_labels, metric="cosine", sample_size=5000,
                                  random_state=seed)
    print(f"RELAY: S7 cohort token is the expected one: "
          f"{'yes' if cohort_token == EXPECTED_TOKENS['cohort'] else 'no'}", flush=True)
    print(f"RELAY: S7 cluster A token is the expected one: "
          f"{'yes' if sub_token == EXPECTED_TOKENS['cluster_a'] else 'no'}", flush=True)
    print(f"RELAY: S7 cluster sizes A {int(in_a.sum())} B {int((~in_a).sum())}, "
          f"cluster A nested silhouette {silhouette:.2f}", flush=True)


if __name__ == "__main__":
    main()
