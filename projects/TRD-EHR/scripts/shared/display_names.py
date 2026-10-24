"""The names figures print for classifiers, encoders and retrieval arms.

Figure text uses the paper's names, never a code identifier: a reader sees
"XGBoost", not "xgboost" or "Xgboost", and "Qwen3-Embedding-8B", not the
directory name. One map per kind, so every producer prints the same words.
"""

CLASSIFIER_DISPLAY = {
    "logistic_regression": "Logistic regression",
    "random_forest": "Random forest",
    "gradient_boosting": "Gradient boosting",
    "xgboost": "XGBoost",
}

# Encoder directory name to the name the captions use.
ENCODER_DISPLAY = {
    "bge-small-en-v1.5": "bge-small-en-v1.5",
    "bge-en-icl": "bge-en-icl",
    "Qwen-Qwen3-Embedding-4B": "Qwen3-Embedding-4B",
    "Qwen-Qwen3-Embedding-8B": "Qwen3-Embedding-8B",
}

# The retrieval arm the paper calls logistic-regression-weighted. Its code name is
# importance-weighted, which no figure prints.
WEIGHTED_RETRIEVAL_DISPLAY = "logistic-regression-weighted"


def classifier_display(name: str) -> str:
    """The paper's name for a classifier key, or the key unchanged if it has none."""
    return CLASSIFIER_DISPLAY.get(name, name)


def encoder_display(name: str) -> str:
    """The paper's name for an encoder directory, or the name unchanged if it has none."""
    return ENCODER_DISPLAY.get(name, name)
