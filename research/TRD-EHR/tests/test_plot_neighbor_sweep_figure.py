"""Guards on the Figure-4-style panel drawn for every encoder.

(a) The primary encoder, whose per-patient classifier test predictions are on disk,
    keeps its bootstrapped classifier lines and its retrieval-minus-classifier contrasts.
(b) Another encoder, with no per-patient classifier predictions, still draws: each
    classifier line comes from classical_ml_results_*.json with its interval, the
    feature-vector line from FEATURE_RESULTS_DIR, and no retrieval-minus-classifier
    contrast is written.
(c) A classifier line with no source at all is fatal, never silently dropped.

Synthetic data only; nothing here reads a real RESULTS_DIR.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.append(str(Path(__file__).parent.parent))

from scripts.pipeline.predictions import plot_neighbor_sweep_figure as figure

N = 300
KS = np.array([1, 3, 10, 30, 100, 299])


def write_sweep(results_dir: Path, rng: np.random.Generator) -> None:
    """The files neighbor_count_sweep leaves in RESULTS_DIR/neighbor_count_sweep."""
    sweep = results_dir / figure.SWEEP_DIR_NAME
    sweep.mkdir(parents=True)
    ids = [f"p{i}" for i in range(N)]
    y = (rng.random(N) < 0.25).astype(int)
    for name, signal in (("best_k_predictions_alpha2.csv", 0.3),
                         ("best_k_predictions_alpha1.csv", 0.3),
                         ("best_k_predictions_alpha1_plain.csv", 0.2)):
        pd.DataFrame({"anchor_patient_id": ids, "true_label": y,
                      "predicted_risk": signal * y + rng.random(N)}).to_csv(sweep / name, index=False)
    pd.concat([pd.DataFrame({"metric": m, "alpha": 1.0, "n_neighbors": KS,
                             "roc_auc": base + 0.01 * np.log10(KS)})
               for m, base in (("weighted", 0.60), ("plain", 0.59))]).to_csv(sweep / "sweep_curve.csv", index=False)
    pd.concat([pd.DataFrame({"metric": m, "alpha": 1.0, "n_neighbors": KS,
                             "roc_auc": 0.6, "ci_low": 0.57, "ci_high": 0.63})
               for m in ("weighted", "plain")]).to_csv(sweep / "sweep_intervals.csv", index=False)
    pd.DataFrame({"n_neighbors": KS, "roc_auc": 0.5, "ci_low": 0.48, "ci_high": 0.52}).to_csv(
        sweep / figure.RANDOM_CURVE, index=False)
    pd.DataFrame({"roc_auc": 0.5 + rng.normal(0, 0.01, 40)}).to_csv(
        sweep / figure.RANDOM_DRAWS_AT_BEST, index=False)


def write_classifier_predictions(results_dir: Path, rng: np.random.Generator) -> None:
    """Per-patient test predictions, as classical_ml writes them for the primary encoder."""
    labels = pd.read_csv(results_dir / figure.SWEEP_DIR_NAME / "best_k_predictions_alpha1.csv")
    for source, model in (("EMBEDDED", "logistic_regression"), ("FEATURE", "xgboost")):
        pd.DataFrame({"patient_id": labels.anchor_patient_id, "true_label": labels.true_label,
                      model: 0.4 * labels.true_label + rng.random(N)}).to_parquet(
            results_dir / f"test_predictions_{source}.parquet", index=False)


def write_summary(results_dir: Path, source: str, model: str, auc: tuple) -> None:
    """classical_ml_results_{source}.json with one model's AUC and interval."""
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / f"classical_ml_results_{source}.json").write_text(json.dumps(
        {model: {"roc_score": auc[0], "roc_score_ci_low": auc[1], "roc_score_ci_high": auc[2]}}))


@pytest.fixture
def run(monkeypatch):
    """Run main() on a RESULTS_DIR and return (reference lines drawn, deltas written)."""
    def go(results_dir: Path, feature_dir: Path = None):
        monkeypatch.setenv("RESULTS_DIR", str(results_dir))
        if feature_dir is None:
            monkeypatch.delenv("FEATURE_RESULTS_DIR", raising=False)
        else:
            monkeypatch.setenv("FEATURE_RESULTS_DIR", str(feature_dir))
        drawn = {}
        monkeypatch.setattr(figure, "draw", lambda curve, intervals, references, path, random=None:
                            drawn.update(references=references, random=random, path=path))
        figure.main()
        deltas = json.loads((results_dir / figure.SWEEP_DIR_NAME / figure.DELTAS_NAME).read_text())
        return drawn, deltas
    return go


def test_primary_encoder_keeps_bootstrapped_lines_and_contrasts(tmp_path, run):
    rng = np.random.default_rng(1)
    primary = tmp_path / "primary"
    write_sweep(primary, rng)
    write_classifier_predictions(primary, rng)
    drawn, deltas = run(primary, feature_dir=primary)
    assert set(drawn["references"]) == {label for label, *_ in figure.REFERENCES}
    for label, *_ in figure.REFERENCES:
        assert f"best_retrieval_minus_{label}" in deltas
        auc, low, high = drawn["references"][label]
        assert low < auc < high
    assert "weighted_minus_plain_at_own_best_k" in deltas
    assert drawn["random"] is not None


def test_other_encoder_reads_summary_lines_and_writes_no_classifier_contrast(tmp_path, run):
    rng = np.random.default_rng(2)
    primary, other = tmp_path / "primary", tmp_path / "other"
    write_sweep(other, rng)
    write_summary(other, "EMBEDDED", "logistic_regression", (0.645, 0.629, 0.660))
    write_summary(primary, "FEATURE", "xgboost", (0.651, 0.636, 0.666))
    # A FEATURE summary in the encoder's own directory must lose to the primary's.
    write_summary(other, "FEATURE", "xgboost", (0.9, 0.89, 0.91))
    drawn, deltas = run(other, feature_dir=primary)
    assert drawn["references"] == {"EMBEDDED logistic regression": (0.645, 0.629, 0.660),
                                   "FEATURE XGBoost": (0.651, 0.636, 0.666)}
    assert not any(key.startswith("best_retrieval_minus_") for key in deltas)
    assert {"weighted_minus_plain_at_own_best_k", "weighted_minus_random_at_own_best_k",
            "plain_minus_random_at_own_best_k"} <= set(deltas)


def test_primary_feature_predictions_are_not_paired_with_another_encoder(tmp_path, run):
    """The primary's per-patient FEATURE predictions give the line a summary, not a contrast."""
    rng = np.random.default_rng(3)
    primary, other = tmp_path / "primary", tmp_path / "other"
    write_sweep(primary, rng)
    write_classifier_predictions(primary, rng)
    write_summary(primary, "FEATURE", "xgboost", (0.651, 0.636, 0.666))
    write_sweep(other, rng)
    write_summary(other, "EMBEDDED", "logistic_regression", (0.645, 0.629, 0.660))
    drawn, deltas = run(other, feature_dir=primary)
    assert drawn["references"]["FEATURE XGBoost"] == (0.651, 0.636, 0.666)
    assert not any(key.startswith("best_retrieval_minus_") for key in deltas)


def test_a_classifier_line_with_no_source_is_fatal(tmp_path, run):
    rng = np.random.default_rng(4)
    other = tmp_path / "other"
    write_sweep(other, rng)
    write_summary(other, "EMBEDDED", "logistic_regression", (0.645, 0.629, 0.660))
    with pytest.raises(FileNotFoundError):
        run(other, feature_dir=tmp_path / "nowhere")
