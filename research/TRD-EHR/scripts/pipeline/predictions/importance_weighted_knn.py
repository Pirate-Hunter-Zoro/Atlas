"""Importance-weighted nearest-neighbour similarity over the embedded narratives.

Plain cosine similarity over a 4096-dimensional embedding treats every dimension as
equally informative about treatment-resistant depression, which they are not: the
elastic-net logistic regression fitted on the same embeddings keeps a non-zero
coefficient on a few hundred dimensions and drives the rest to exactly zero. This
module reuses those coefficients as a diagonal metric, so two patients count as
neighbours when they agree on the dimensions that carry TRD signal and are not
penalised for disagreeing on the ones that carry none.

The similarity, for anchor x and candidate y, with the logistic regression's own
standardiser (mu, sigma) and its coefficient vector beta:

    z_d      = (x_d - mu_d) / sigma_d                 the space beta was fitted in
    w_d      = |beta_d| / sum_e |beta_e|              the dimension's share of importance
    <x, y>_w = sum_d w_d * z_d(x) * z_d(y)            a weighted inner product
    sim(x,y) = <x, y>_w / sqrt(<x, x>_w * <y, y>_w)   its cosine

Equivalently: scale every standardised dimension by sqrt(w_d), L2-normalise the row,
and take an ordinary dot product. That is what to_weighted_space does, which is why the
whole anchor-by-pool similarity matrix is one matmul. The normalisation makes the
overall scale of w irrelevant, so w is normalised to sum to one only for readability.

The same number does both jobs the sweep needs. It ranks candidates, so it selects the
k nearest; and clamped at zero and raised to alpha it is the weight in the risk score

    risk(anchor) = sum_i w_i * trd_flag_i / sum_i w_i

over those k neighbours, exactly the form the published cosine arm uses in
trd_prediction_computation.calculated_weighted_risk.

One honesty note about what is held out. The anchors are the test split and the
candidate pool is everything else, so no anchor's own label reaches its risk score. The
coefficients come from a fit on the pool patients, which is the same information a
k-nearest-neighbour rule already uses when it reads a neighbour's label -- but it does
mean this metric is supervised, and comparing it with plain cosine is a comparison of a
supervised metric against an unsupervised one rather than of two retrieval tricks.
"""

import os
import sqlite3
from pathlib import Path
from typing import Tuple

import joblib
import numpy as np

from dotenv import load_dotenv
load_dotenv()

from scripts.shared.utils import VectorSource
from scripts.pipeline.predictions.classical_ml import model_cache_path

# Which fitted classifier supplies the dimension weights. Only the linear model has one
# coefficient per embedding dimension; a tree ensemble's importances are splits, not a
# metric, and do not carry a sign or a scale that means anything in an inner product.
IMPORTANCE_MODEL_NAME = 'logistic_regression'

# Fractions of the dimension list quoted in the concentration summary.
CONCENTRATION_FRACTIONS = (0.01, 0.02, 0.05, 0.10, 0.25, 0.50)


def load_dimension_weights(model_name: str = IMPORTANCE_MODEL_NAME) -> Tuple[np.ndarray, object]:
    """Read the fitted embedded-space classifier and return its per-dimension weights.

    Args:
        model_name (str, optional): Cached classifier to read. Defaults to
            IMPORTANCE_MODEL_NAME; anything else must still be a linear model with a
            coef_ of one row.

    Returns:
        Tuple[np.ndarray, object]: (weights of shape (n_dimensions,), non-negative and
            summing to one, indexed by embedding dimension; the fitted StandardScaler
            those coefficients were learnt against).
    """
    cache_path = model_cache_path(model_name, VectorSource.EMBEDDED)
    if not cache_path.exists():
        raise FileNotFoundError(
            f"No fitted {model_name} for the embedded representation at {cache_path}. "
            "Run scripts.pipeline.predictions.classical_ml first -- this metric is its coefficients."
        )
    fitted_pipeline = joblib.load(cache_path).best_estimator_
    # The embedded matrix is all-numeric, so the ColumnTransformer's 'num' branch is the
    # whole preprocessor and its column order is the embedding dimension order.
    scaler = fitted_pipeline.named_steps['preprocess'].named_transformers_['num']
    coefficients = np.asarray(fitted_pipeline.named_steps['model'].coef_[0], dtype=np.float64)
    magnitudes = np.abs(coefficients)
    total = magnitudes.sum()
    if total == 0:
        raise ValueError(f"{model_name} kept no non-zero coefficient; there is no metric to build.")
    return magnitudes / total, scaler


def concentration_summary(weights: np.ndarray) -> dict:
    """Describe how few dimensions hold how much of the importance mass.

    Args:
        weights (np.ndarray): Output of load_dimension_weights.

    Returns:
        dict: Dimension count, non-zero count, and the share of total importance held by
            the top fraction of dimensions for each of CONCENTRATION_FRACTIONS.
    """
    descending = np.sort(weights)[::-1]
    cumulative = np.cumsum(descending)
    summary = {
        'n_dimensions': int(weights.size),
        'n_nonzero_dimensions': int((weights > 0).sum()),
        'share_of_importance_by_top_fraction_of_dimensions': {},
    }
    for fraction in CONCENTRATION_FRACTIONS:
        count = max(1, int(round(weights.size * fraction)))
        summary['share_of_importance_by_top_fraction_of_dimensions'][f"top_{fraction:.2%}"] = {
            'n_dimensions': count,
            'share': float(cumulative[count - 1]),
        }
    return summary


def to_weighted_space(vectors: np.ndarray, scaler, weights: np.ndarray) -> np.ndarray:
    """Standardise, importance-scale and L2-normalise, so a dot product is the similarity.

    Args:
        vectors (np.ndarray): Raw embeddings, shape (n_patients, n_dimensions).
        scaler: The fitted StandardScaler from load_dimension_weights.
        weights (np.ndarray): The dimension weights from load_dimension_weights.

    Returns:
        np.ndarray: float32 array of the same shape with unit rows under the weighted
            inner product. Rows that land at the origin -- a patient exactly average on
            every dimension the classifier kept -- are left as zeros, which makes their
            similarity to everyone zero rather than undefined.
    """
    standardised = (vectors.astype(np.float64) - scaler.mean_) / scaler.scale_
    scaled = standardised * np.sqrt(weights)
    norms = np.linalg.norm(scaled, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (scaled / norms).astype(np.float32)


def load_raw_embeddings(patient_ids: list[str]) -> np.ndarray:
    """Fetch raw, un-normalised embeddings for the given patients, in the given order.

    Retriever already reads this table but L2-normalises its matrix in place, and this
    metric needs the vectors before that: standardising has to happen against the
    classifier's own means, which were learnt on raw embeddings.

    Args:
        patient_ids (list[str]): Patient IDs, in the order the rows should come back.

    Returns:
        np.ndarray: float32 array of shape (len(patient_ids), n_dimensions).
    """
    connection = sqlite3.connect(Path(os.environ['EMBEDDINGS_DIR']) / 'embeddings.db')
    try:
        rows = dict(connection.execute("SELECT patient_id, embedding FROM embeddings").fetchall())
    finally:
        connection.close()
    missing = [pid for pid in patient_ids if pid not in rows]
    if missing:
        raise ValueError(f"{len(missing)} requested patients have no embedding, first is {missing[0]}")
    return np.vstack([np.frombuffer(rows[pid], dtype=np.float32) for pid in patient_ids])


def candidate_pool_ids(exclude_ids: set[str]) -> list[str]:
    """The neighbour pool: every embedded patient with a narrative, minus the anchors.

    The same two conditions Retriever imposes, so this sweep searches the identical pool
    the published cosine arm searched and the two ROC numbers are comparable.

    Args:
        exclude_ids (set[str]): Anchor IDs, which must never be their own neighbours.

    Returns:
        list[str]: Sorted pool IDs.
    """
    connection = sqlite3.connect(Path(os.environ['EMBEDDINGS_DIR']) / 'embeddings.db')
    try:
        embedded = [row[0] for row in connection.execute("SELECT patient_id FROM embeddings").fetchall()]
    finally:
        connection.close()
    narrated = {path.stem for path in Path(os.environ['NARRATIVES_DIR']).glob("*.md")}
    absent = [pid for pid in embedded if pid not in narrated]
    if absent:
        raise ValueError(f"{len(absent)} embedded patients have no narrative, first is {absent[0]}")
    return sorted(pid for pid in embedded if pid not in exclude_ids)


def neighbour_weights(similarities: np.ndarray, alpha: float) -> np.ndarray:
    """Turn similarities into the non-negative weights of the risk score.

    Args:
        similarities (np.ndarray): Weighted cosine values, any shape, in [-1, 1].
        alpha (float): Sharpening exponent. One uses the similarity itself; larger values
            concentrate the risk score on the closest neighbours, which is the knob
            WEIGHTING_EXPONENT turns for the published cosine arm.

    Returns:
        np.ndarray: Weights of the same shape, zero wherever the similarity was negative.
    """
    return np.clip(similarities, 0.0, None) ** alpha
