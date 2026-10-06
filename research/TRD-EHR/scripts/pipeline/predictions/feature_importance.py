import os
import json
from pathlib import Path
import copy
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier
from scipy.stats import spearmanr

from scripts.pipeline.predictions.classical_ml import make_classifier
from scripts.shared.utils import VectorSource
from scripts.shared.feature_display_names import humanize_feature_names
from scripts.shared.display_names import classifier_display
from scripts.pipeline.predictions.classical_ml import load_data_set, model_cache_path
from scripts.pipeline.predictions.create_train_test_split import create_train_test_split

from dotenv import load_dotenv
load_dotenv()


PCA_K_VALUES = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
MODEL_NAMES = ("logistic_regression", "random_forest", "gradient_boosting", "xgboost")
TOP_K = 20

# Figures S1-S3 are placed at 5.8in from a 10in canvas, a 0.58 downscale; these sizes
# print at about 8-9pt there.
OVERLAY_FONT_SIZES = {"tick": 14, "label": 15, "title": 16, "legend": 13}
FIGURE_DPI = 220
# The model-agnostic curve of Figure S2, ranked by correlation with the outcome itself.
OUTCOME_CURVE_LABEL = "TRD outcome (model-agnostic)"


class CacheMiss(FileNotFoundError):
    """A redraw found no cached model, and a redraw never refits."""

def load_best_params(model_name: str, source: VectorSource) -> dict:
    """From the recorded results, find the best parameters associated with the given model operating on the input vector source

    Args:
        model_name (str): Classifier
        source (VectorSource): Embedded or feature

    Returns:
        dict: Pipeline-prefixed parameters
    """
    results_json_path = Path(os.environ['RESULTS_DIR']) / f"grid_search_ml_results_{source.name}.json"
    with open(results_json_path, 'r') as f:
        results = json.load(f)
    return results[model_name]["Best Parameters"]

def refit_best_model(
    model_name: str,
    source: VectorSource,
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    cache_only: bool = False,
) -> Pipeline:
    """Given the model, load the cached fitted best estimator if available, otherwise load the best hyperparameters and use them to refit a fresh pipeline from the grid-search best params

    Args:
        model_name (str): Name of model to reference results with
        source (VectorSource): Feature or embedded vectors
        X_train (pd.DataFrame): Training inputs to fit with
        y_train (np.ndarray): Training outputs to fit with
        cache_only (bool, optional): Refuse rather than refit on a cache miss. A redraw
            sets it: a refit can land on a different fit of equal discrimination, and
            the supplement quotes this fit's coefficient counts.

    Returns:
        Pipeline: fitted sklearn Pipeline
    """
    cache_path = model_cache_path(model_name, source)
    if cache_path.exists():
        print(f"Loading cached best estimator for {model_name} on {source.name}...", flush=True)
        return joblib.load(cache_path).best_estimator_
    if cache_only:
        raise CacheMiss(f"No cached best estimator for {model_name}_{source.name}; a redraw does not refit.")
    print(f"Cache miss for {model_name}_{source.name}; refitting from grid-search best params...", flush=True)
    seed = int(os.environ['SEED'])
    models = {
        "logistic_regression": LogisticRegression(max_iter=1000, random_state=seed),
        "random_forest": RandomForestClassifier(random_state=seed),
        "gradient_boosting": GradientBoostingClassifier(random_state=seed),
        "xgboost": XGBClassifier(random_state=seed, eval_metric="logloss", n_jobs=1)
    }
    base_estimator_pipeline = make_classifier(models[model_name])
    hyperparams = load_best_params(model_name, source)
    base_estimator_pipeline.set_params(**hyperparams)
    base_estimator_pipeline.fit(X_train, y_train)
    return base_estimator_pipeline

def extract_feature_importances(
    pipeline: Pipeline,
    model_name: str,
) -> tuple[np.ndarray, list[str]]:
    """From fitted pipeline, extract importance value for each feature

    Args:
        pipeline (Pipeline): Fitted model
        model_name (str): Name of model

    Returns:
        tuple[np.ndarray, list[str]]: Feature importances paired with their names
    """
    steps = pipeline.named_steps

    # This preprocessor has already been fitted with its learned categories from training
    preprocessor = steps['preprocess']
    # Post encoding labels - e.g. branch__column_value style for categorical fields
    feature_names = list(preprocessor.get_feature_names_out())

    # Grab the model's importances
    model = steps['model'] # Already fitted model
    if model_name == "logistic_regression":
        # The coefficients logistic regression applies to each feature ARE the importances
        importances = model.coef_[0] # Grab index zero because originally of shape (1, n_features)
    else:
        importances = model.feature_importances_

    return (importances, feature_names)

def plot_feature_importance(
    importances: np.ndarray,
    feature_names: list[str],
    model_name: str,
    top_k: int=20,
    direction_signs: np.ndarray | None = None,
):
    """Helper method to plot the different feature importances of the given model

    Args:
        importances (np.ndarray): Importances of each feature from the learning model
        feature_names (list[str]): Names of each feature
        model_name (str): Name of classifier - e.g. logistic_regression, etc.
        direction_signs (np.ndarray | None, optional): Whether an increase in the numeric feature increases or decreases risk score. Defaults to None.
        top_k (int, optional): How many bars (features) to display. Defaults to 20.
    """
    magnitudes = np.abs(importances)
    # Only grab the top k sorted (reverse order for higher magnitude first) indices
    sorted_mag_indices = np.argsort(magnitudes)[::-1][:top_k]
    top_importances = importances[sorted_mag_indices]
    top_names = [feature_names[i] for i in sorted_mag_indices]
    top_directions = None
    if direction_signs is not None:
        top_directions = direction_signs[sorted_mag_indices]

    if model_name == "logistic_regression":
        colors = ['steelblue' if val >= 0 else 'firebrick' for val in top_importances]
    elif top_directions is None:
        colors = 'steelblue' # One raw string works with matplotlib as well
    else:
        colors = ['steelblue' if val >= 0 else 'firebrick' for val in top_directions.tolist()]

    # Sizing: these panels are placed in the manuscript at 6in wide, so what
    # matters is the label size AFTER downscaling, not the nominal font size.
    # Two constraints have to hold at once. The type has to survive the
    # downscale, and the panel has to be short enough on the page that two of
    # them fit inside the 9in text column: a 7.5x6.8in panel arrives 5.44in
    # tall at 6in wide, so only one fits per page and the remainder of the page
    # is left blank -- which is the gap this layout is fixing. Widening to 10in
    # and pacing the rows at 0.255in puts the panel near 3.7in on the page (two
    # per page, no gap), and the label size rises from 12 to 16pt to pay for
    # the deeper 0.6x downscale, so the labels land where they did before.
    LABEL_POINT_SIZE = 16
    fig, ax = plt.subplots(figsize=(10.0, max(4.5, 1.0 + top_k * 0.255)))
    # Create bars of length corresponding to importance magnitudes
    ax.barh(range(len(top_names)), np.abs(top_importances), color=colors)
    ax.set_yticks(range(len(top_names)))
    ax.set_yticklabels(humanize_feature_names(top_names), fontsize=LABEL_POINT_SIZE)
    ax.tick_params(axis='x', labelsize=LABEL_POINT_SIZE)
    ax.invert_yaxis()
    ax.set_xlabel("Feature importance (magnitude)", fontsize=LABEL_POINT_SIZE + 1)
    # NOTE: assigning the conditional to a name first is load-bearing. Inlined
    # without parentheses, Python's precedence binds the conditional to the
    # second operand only, so the "direction unspecified" branch silently drops
    # the model name from the title.
    direction_known = model_name == "logistic_regression" or direction_signs is not None
    suffix = "blue: raises TRD risk, red: lowers TRD risk" if direction_known \
        else "direction unspecified"
    # Title is split across two lines: on one line the colour key overruns the
    # figure width and gets clipped.
    pretty_name = classifier_display(model_name)
    ax.set_title(f"{pretty_name}\n({suffix})", fontsize=LABEL_POINT_SIZE, fontweight='bold')
    ax.grid(axis='x', linestyle=':', linewidth=0.8, alpha=0.6)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    save_path = Path(os.environ['RESULTS_DIR']) / "feature_importance" /\
        f"feature_importance_{model_name}.png"
    os.makedirs(save_path.parent, exist_ok=True)
    fig.savefig(str(save_path), dpi=FIGURE_DPI)
    plt.close(fig)

def compute_univariate_spearman(
    X: pd.DataFrame,
    risk_scores: np.ndarray,
    feature_names: list[str],
) -> np.ndarray:
    """Find spearman correlation between each column of X and y

    Args:
        X (pd.DataFrame): post-ColumnTransformer feature matrix (imputed, scaled, one-hot-encoded, bool-cast) (completely numeric)
        risk_scores (np.ndarray): TRD risk scores predicted by some model, shape (n_samples,)
        feature_names (list[str]): Column names of X.columns

    Returns:
        np.ndarray: (n_features,) - each spearman correlation over all attribute indices in X
    """
    if X.shape[1] != len(feature_names):
        raise ValueError(f"Error, expected {len(feature_names)} columns in X but found {X.shape[1]}")
    # For each column, compute spearman correlation between X[col] and y
    result = spearmanr(X, risk_scores).statistic # Works with X being 2D and y being 1D
    # Output is of shape (n_features + 1, n_features + 1) - we care about the last row, first n_features
    return result[result.shape[0]-1, 0:len(feature_names)]

def count_nonzero_lr_coefficients(pipeline: Pipeline) -> tuple[int,int]:
    """Given a trained logistic regression learning model, find the number of non-zero (or close to it) coefficients

    Args:
        pipeline (Pipeline): "model" step is a LogisticRegression

    Returns:
        tuple[int,int]: (nonzero_count, total_count)
    """
    model = pipeline.named_steps["model"]
    if not isinstance(model, LogisticRegression):
        raise TypeError(f"Expected model of type {LogisticRegression.__name__} but received {type(model).__name__}...")
    feature_coefficients = model.coef_[0] # index zero since shape is (1, n_features)
    total = len(feature_coefficients)
    nonzero = len(feature_coefficients[np.abs(feature_coefficients) > 1e-10])
    return (nonzero, total)

def plot_cumulative_magnitude_overlay(
    magnitudes_by_label: dict[str, np.ndarray],
    xlabel: str,
    ylabel: str,
    title: str,
    filename: str,
):
    """Plot of overlapping results of cumulative fraction of magnitude against output for each dimension over all the given model (or baseline) results

    Args:
        magnitudes_by_label (dict[str, np.ndarray]): Magnitude results for various models/schemes
        xlabel (str): x-axis text
        ylabel (str): y-axis text
        title (str): plot title text
        filename (str): final segment of save path
    """
    fig, ax = plt.subplots(figsize=(10,6))
    ax.axhline(0.8, linestyle='--', color='gray', alpha=0.5)
    ax.axhline(0.9, linestyle='--', color='gray', alpha=0.5)

    # Plot each model's correlation output
    for label, magnitudes in magnitudes_by_label.items():
        fraction = cumulative_fraction(magnitudes)
        # Create plot of increasing 'rank-1' on the x-axis, farther to the left is where we have added the highest remaining magnitude correlation
        ranks = np.arange(1, len(fraction)+1)
        knee_80, knee_90 = knees(magnitudes)
        ax.plot(ranks, fraction, linewidth=2, label=f"{label} (K₈₀={knee_80}, K₉₀={knee_90})")
    ax.legend(loc='lower right', fontsize=OVERLAY_FONT_SIZES["legend"])
    ax.set_xlabel(xlabel, fontsize=OVERLAY_FONT_SIZES["label"])
    ax.set_ylabel(ylabel, fontsize=OVERLAY_FONT_SIZES["label"])
    ax.set_title(title, fontsize=OVERLAY_FONT_SIZES["title"])
    ax.tick_params(axis='both', labelsize=OVERLAY_FONT_SIZES["tick"])
    fig.tight_layout()
    save_path = Path(os.environ['RESULTS_DIR']) / "feature_importance" / filename
    os.makedirs(save_path.parent, exist_ok=True)
    fig.savefig(str(save_path), dpi=FIGURE_DPI)
    plt.close(fig)


def cumulative_fraction(magnitudes: np.ndarray) -> np.ndarray:
    """Cumulative share of total absolute mass, dimensions ranked largest first."""
    cumulative = np.cumsum(np.sort(np.abs(magnitudes))[::-1]) # Last rank holds total mass
    return cumulative / cumulative[-1]


def knees(magnitudes: np.ndarray) -> tuple[int, int]:
    """(K80, K90): the fewest top-ranked dimensions holding 80% and 90% of the mass."""
    fraction = cumulative_fraction(magnitudes)
    return int(np.searchsorted(fraction, 0.8) + 1), int(np.searchsorted(fraction, 0.9) + 1)

def pca_cache_path(model_name: str, k: int) -> Path:
    """Given the model name and the number of PCA dimensions, return resulting path where the model should be saved

    Args:
        model_name (str): Name of model (e.g. 'logistic_regression')
        k (int): Number of PCA dimensions

    Returns:
        Path: Resulting save path
    """
    save_path = Path(os.environ['RESULTS_DIR']) / "trained_models_pca" / f"{model_name}_K={k}.joblib"
    os.makedirs(save_path.parent, exist_ok=True)
    return save_path

def plot_pca_k_vs_roc(
    model_name: str,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: np.ndarray,
    y_test: np.ndarray,
    cache_only: bool = False,
):
    """For each K in a pre-set list of values, refit one of the four classifiers on the embedded
  vectors projected to K principal components, score it on the held-out test set, and plot ROC AUC
  versus K

    Args:
        model_name (str): Specified ML model
        X_train (pd.DataFrame): Embedded vectors
        X_test (pd.DataFrame): Held-out embedded vectors
        y_train (np.ndarray): Train labels
        y_test (np.ndarray): Held-out labels
        cache_only (bool, optional): Refuse rather than refit a PCA pipeline that is not
            cached, as refit_best_model does.

    Returns:
        list[float]: Test ROC AUC at each retained component count.
    """
    base_models = {
        "logistic_regression": LogisticRegression(max_iter=1000, random_state=int(os.environ['SEED'])),
        "random_forest": RandomForestClassifier(random_state=int(os.environ['SEED'])),
        "gradient_boosting": GradientBoostingClassifier(random_state=int(os.environ['SEED'])),
        "xgboost": XGBClassifier(random_state=int(os.environ['SEED']), eval_metric='logloss')
    }
    best_params = load_best_params(model_name, VectorSource.EMBEDDED)
    auc_scores = []
    # A cache-only redraw loads no training rows; the held-out rows have the same width,
    # and both splits hold far more patients than the largest K.
    reference = X_test if X_train is None else X_train
    RELEVANT_PCA_VALUES = [v for v in PCA_K_VALUES if v <= min(reference.shape)]
    
    for k in RELEVANT_PCA_VALUES:
        # Different number of PCA dimensions each time
        pca_save_path = pca_cache_path(model_name, k)
        if pca_save_path.exists() and int(os.environ['SCRUB_TRAINED_MODELS']) == 0:
            print(f"Loading cached PCA-K{k} pipeline for {model_name}...", flush=True)
            pipeline = joblib.load(pca_save_path)
        elif cache_only:
            raise CacheMiss(f"No cached PCA-K{k} pipeline for {model_name}; a redraw does not refit.")
        else:
            pipeline = Pipeline(steps=\
                [
                    ("scale", StandardScaler()),
                    ("pca", PCA(n_components=k, random_state=int(os.environ['SEED']))),
                    ("model", base_models[model_name])
                ]
            )
            pipeline.set_params(**best_params)
            pipeline.fit(X_train, y_train)
            joblib.dump(pipeline, pca_save_path)
        y_pred = pipeline.predict_proba(X_test)[:,1]
        score = float(roc_auc_score(y_true=y_test, y_score=y_pred))
        auc_scores.append(score)
    save_dir = Path(os.environ['RESULTS_DIR']) / 'feature_importance'
    os.makedirs(save_dir, exist_ok=True)
    # The scores are kept beside the figure, so a later restyle reads them and loads no model.
    (save_dir / f"pca_sweep_{model_name}_EMBEDDED.json").write_text(json.dumps(
        {"pca_components": RELEVANT_PCA_VALUES, "roc_auc": auc_scores}, indent=2))
    draw_pca_sweep(model_name, RELEVANT_PCA_VALUES, auc_scores,
                   save_dir / f"feature_importance_pca_sweep_{model_name}_EMBEDDED.png")
    return auc_scores


def draw_pca_sweep(model_name: str, ks: list[int], auc_scores: list[float], save_path: Path):
    """Figure S3, one panel: ROC AUC against retained principal components.

    Args:
        model_name (str): Classifier key; the title prints its display name.
        ks (list[int]): Component counts, powers of 2.
        auc_scores (list[float]): Test ROC AUC at each.
        save_path (Path): Destination PNG.
    """
    fig, ax = plt.subplots(figsize=(10,6))
    ax.plot(ks, auc_scores, marker='o', color='steelblue', linewidth=2)
    ax.set_xscale('log', base=2) # Logarithmic x-scale since k-values are powers of 2
    for k, auc in zip(ks, auc_scores):
        ax.text(k, auc, f"{auc:.3f}", fontsize=OVERLAY_FONT_SIZES["legend"])
    ax.set_xlabel("Retained principal components, K (log scale)", fontsize=OVERLAY_FONT_SIZES["label"])
    ax.set_ylabel("Test-set ROC AUC", fontsize=OVERLAY_FONT_SIZES["label"])
    ax.set_title(f"{classifier_display(model_name)}, embedded representation",
                 fontsize=OVERLAY_FONT_SIZES["title"])
    ax.tick_params(axis='both', labelsize=OVERLAY_FONT_SIZES["tick"])
    fig.tight_layout()
    fig.savefig(str(save_path), dpi=FIGURE_DPI)
    plt.close(fig)

def write_feature_importance_summary(summary: dict[str, list[dict]]):
    """Record name, feature importance, and feature importance direction of each feature over all models

    Args:
        summary (dict[str, list[dict]]): Results
    """
    save_path = Path(os.environ['RESULTS_DIR']) / "feature_importance" / "feature_importance_summary.json"
    os.makedirs(save_path.parent, exist_ok=True)
    cleaned_summary = copy.deepcopy(summary)
    for model in summary.keys():
        # JSON chokes on np.float64 and np.int64
        for row in cleaned_summary[model]:
            row["importance"] = float(row["importance"])
            row["sign"] = int(row["sign"])
    with open(save_path, 'w') as f:
        json.dump(cleaned_summary, f, indent=4)

def embedded_pass(train_ids, test_ids, cache_only: bool = False) -> dict:
    """Figures S1-S3: the cumulative overlays and the PCA sweeps, embedded representation.

    Args:
        train_ids: Training patient ids, as create_train_test_split.
        test_ids: Held-out patient ids.
        cache_only (bool, optional): Draw only from cached fitted models and raise
            CacheMiss rather than refit; the training rows are not even loaded.

    Returns:
        dict: What the figures print that a redraw can be checked against: the logistic
            regression's non-zero coefficient count and width, and each classifier's
            importance knees (K80, K90).
    """
    source = VectorSource.EMBEDDED
    print(f"Feature importance pass: {source.name} running...", flush=True)
    (X_train, y_train) = (None, None) if cache_only else load_data_set(train_ids, source)
    (X_test, y_test) = load_data_set(test_ids, source)
    correlations_by_label: dict[str, np.ndarray] = {}
    importances_by_label: dict[str, np.ndarray] = {}
    feature_name_dims = [str(col) for col in X_test.columns]
    label_correlations = compute_univariate_spearman(X_test, y_test, feature_name_dims)
    correlations_by_label[OUTCOME_CURVE_LABEL] = label_correlations
    checks = {"importance_knees": {}}
    for model_name in MODEL_NAMES:
        print(f"Running {model_name} feature importance under {source.name} vectors...")
        model_pipeline = refit_best_model(model_name, source, X_train, y_train, cache_only=cache_only)
        (feature_importances, _) = extract_feature_importances(model_pipeline, model_name)
        importances_by_label[classifier_display(model_name)] = feature_importances
        checks["importance_knees"][model_name] = knees(feature_importances)
        if model_name == "logistic_regression":
            (nonzero_count, total_count) = count_nonzero_lr_coefficients(model_pipeline)
            sparsity_path = Path(os.environ['RESULTS_DIR']) / "feature_importance_sparsity.json"
            os.makedirs(sparsity_path.parent, exist_ok=True)
            with open(sparsity_path, 'w') as f:
                json.dump({
                    "nonzero_coefficients": nonzero_count,
                    "total_coefficients": total_count
                }, f, indent=4)
            checks["nonzero_coefficients"] = (nonzero_count, total_count)
        risk_scores = model_pipeline.predict_proba(X_test)[:, 1]
        feature_names = [str(col) for col in X_test.columns]
        correlations = compute_univariate_spearman(X_test, risk_scores, feature_names)
        correlations_by_label[classifier_display(model_name)] = correlations
        plot_pca_k_vs_roc(model_name, X_train, X_test, y_train, y_test, cache_only=cache_only)
    plot_cumulative_magnitude_overlay(
        magnitudes_by_label = correlations_by_label,
        xlabel = "Embedding dimension rank (by |Spearman ρ|, descending)",
        ylabel = f"Cumulative |Spearman ρ| fraction",
        title = "Cumulative correlation, embedded representation",
        filename = f"feature_correlation_cumulative_{VectorSource.EMBEDDED.name}.png",
    )
    plot_cumulative_magnitude_overlay(
        magnitudes_by_label = importances_by_label,
        xlabel = "Embedding dimension rank (by importance, descending)",
        ylabel = f"Cumulative importance fraction",
        title = "Cumulative built-in importance, embedded representation",
        filename = f"feature_importance_cumulative_{VectorSource.EMBEDDED.name}.png",
    )
    return checks


def main():
    (train_ids, test_ids) = create_train_test_split()

    # EMBEDDED pass: single load, classifier loop builds the cumulative-magnitude overlays
    embedded_pass(train_ids, test_ids)

    # FEATURE pass: single load, classifier loop emits per-classifier bar charts
    source = VectorSource.FEATURE
    print(f"Feature importance pass: {source.name} running...", flush=True)
    (X_train, y_train) = load_data_set(train_ids, source=source)
    (X_test, y_test) = load_data_set(test_ids, source=source)

    summary: dict[str, list[dict]] = {}
    for model_name in MODEL_NAMES:
        print(f"Running {model_name} feature importance under {source.name} vectors...")
        model_pipeline = refit_best_model(model_name, source, X_train, y_train)
        (importances, feature_names) = extract_feature_importances(model_pipeline, model_name)
        risk_scores = model_pipeline.predict_proba(X_test)[:, 1]
        # Preprocess X_test so that categoricals are one-hot encoded, bools are int8, etc.
        X_test_preprocessed = model_pipeline.named_steps['preprocess'].transform(X_test)
        if hasattr(X_test_preprocessed, 'toarray'):
            X_test_preprocessed = X_test_preprocessed.toarray()
        correlations = compute_univariate_spearman(X_test_preprocessed, risk_scores, feature_names)
        direction_signs = np.sign(correlations)
        plot_feature_importance(importances, feature_names, model_name, direction_signs=direction_signs)
        sorted_indices = np.argsort(np.abs(importances))[::-1][:TOP_K]
        classifier_top_rows = [{
            "name": feature_names[i],
            "importance": importances[i],
            "sign": direction_signs[i]
        } for i in sorted_indices.tolist()]
        summary[model_name] = classifier_top_rows
    write_feature_importance_summary(summary)


def redraw_embedded():
    """Redraw Figures S1-S3 from the cached fitted models, refitting nothing.

    Prints RELAY: lines carrying the numbers the supplement quotes from these figures, so
    the report says whether the redraw drew the same fit: the logistic regression's
    non-zero coefficients and each classifier's K80/K90.
    """
    (train_ids, test_ids) = create_train_test_split()
    checks = embedded_pass(train_ids, test_ids, cache_only=True)
    nonzero, total = checks["nonzero_coefficients"]
    print(f"RELAY: S1 logistic regression non-zero coefficients {nonzero} of {total}", flush=True)
    for model_name, (k80, k90) in checks["importance_knees"].items():
        print(f"RELAY: S1 {model_name} K80 {k80} K90 {k90}", flush=True)


if __name__=="__main__":
    import sys
    redraw_embedded() if "--redraw-embedded" in sys.argv[1:] else main()
