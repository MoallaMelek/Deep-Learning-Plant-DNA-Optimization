"""FastAPI configuration for the Plant DNA / Protein Expression project."""

from pathlib import Path
from typing import List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = PROJECT_ROOT / "outputs"
OUTPUTS_DIR = OUTPUTS_ROOT / "datasets"
MODELS_WEIGHTS_DIR = PROJECT_ROOT / "models_weights"

DEFAULT_KEYWORD = "insulin"
DEFAULT_PROTEIN_LIMIT = 20
DEFAULT_PRIORITY = "balanced"

AVAILABLE_MODELS: List[str] = [
    "linear_regression",
    "ridge",
    "random_forest",
    "xgboost",
    "lightgbm",
]

CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
]

PROXY_TARGET_WARNING = (
    "This project trains and reports a simulated proxy expression target. "
    "It is not wet-lab validated biological expression data."
)
