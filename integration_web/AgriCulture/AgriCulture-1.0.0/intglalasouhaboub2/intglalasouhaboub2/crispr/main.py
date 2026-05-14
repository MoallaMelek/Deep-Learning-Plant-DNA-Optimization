"""
CRISPR Editing Efficiency Prediction API
-----------------------------------------
POST /predict    → predict editing efficiency from sgRNA features
POST /explain    → predict + SHAP feature-level explanation
GET  /health     → health check
GET  /features   → list expected input fields
"""

import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import shap
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

warnings.filterwarnings("ignore")

# ── Load model ────────────────────────────────────────────────────────────────
MODEL_PATH = Path("model.pkl")


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model file '{MODEL_PATH}' not found. "
            "Place your model.pkl in the same directory as main.py."
        )
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


model = load_model()

# ── Build SHAP explainer once at startup (expensive) ─────────────────────────
# TreeExplainer works directly on GradientBoostingRegressor — no background
# dataset needed, making it fast and exact (not approximate).
explainer = shap.TreeExplainer(model)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="CRISPR Editing Efficiency Predictor",
    description=(
        "Predicts sgRNA editing efficiency (%) from guide sequence "
        "and biological metadata using a trained GradientBoostingRegressor."
    ),
    version="1.1.0",
)


# ── Request / Response schemas ────────────────────────────────────────────────
class PredictionRequest(BaseModel):
    guide_sequence: str = Field(
        ...,
        min_length=20,
        max_length=20,
        description="20-nt sgRNA guide sequence (A/T/G/C only)",
        examples=["ATGCATGCATGCATGCATGC"],
    )
    amplicon_sequence: str = Field(
        ...,
        min_length=1,
        description="Full amplicon DNA sequence",
        examples=["ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGC"],
    )
    within_atac_peak: bool = Field(
        ...,
        description="Whether the cut site is within an ATAC-seq peak (open chromatin)",
        examples=[True],
    )
    leaf_exp: str = Field(
        ...,
        description="Leaf expression level: 'low', 'medium', or 'high'",
        examples=["medium"],
    )
    t0_exp: str = Field(
        ...,
        description="T0 expression level: 'low', 'medium', or 'high'",
        examples=["high"],
    )
    feature: str = Field(
        ...,
        description="Genomic feature type: 'Exo' (exon), 'Int' (intron), or 'Pro' (promoter)",
        examples=["Exo"],
    )

    @field_validator("guide_sequence")
    @classmethod
    def validate_guide(cls, v: str) -> str:
        v = v.upper().strip()
        valid = set("ATGCN")
        bad = [c for c in v if c not in valid]
        if bad:
            raise ValueError(
                f"Invalid nucleotides in guide sequence: {set(bad)}. "
                "Only A, T, G, C, N are allowed."
            )
        return v

    @field_validator("leaf_exp", "t0_exp")
    @classmethod
    def validate_expression(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in {"low", "medium", "high"}:
            raise ValueError(
                f"Expression level must be 'low', 'medium', or 'high'. Got: '{v}'"
            )
        return v

    @field_validator("feature")
    @classmethod
    def validate_feature(cls, v: str) -> str:
        v = v.strip()
        if v not in {"Exo", "Int", "Pro"}:
            raise ValueError(
                f"Feature must be 'Exo', 'Int', or 'Pro'. Got: '{v}'"
            )
        return v


class PredictionResponse(BaseModel):
    predicted_editing_efficiency: float = Field(
        ..., description="Predicted editing efficiency in percent (0–100)"
    )
    prediction_clipped: bool = Field(
        ..., description="True if the raw model output was clipped to [0, 100]"
    )


class FeatureContribution(BaseModel):
    feature: str = Field(..., description="Feature name")
    value: float = Field(..., description="Actual value of this feature for this input")
    shap_value: float = Field(
        ..., description="SHAP contribution: positive = pushes prediction higher"
    )
    direction: str = Field(..., description="'up' or 'down'")


class ExplainResponse(BaseModel):
    predicted_editing_efficiency: float = Field(
        ..., description="Final predicted editing efficiency (%)"
    )
    prediction_clipped: bool = Field(
        ..., description="True if the raw model output was clipped to [0, 100]"
    )
    baseline: float = Field(
        ...,
        description=(
            "Model baseline: average prediction across training data. "
            "SHAP values explain the shift from this value to the final prediction."
        ),
    )
    net_shap_shift: float = Field(
        ..., description="Sum of all SHAP values = prediction minus baseline"
    )
    top_drivers: list[FeatureContribution] = Field(
        ..., description="Top features sorted by absolute SHAP contribution"
    )
    all_contributions: list[FeatureContribution] = Field(
        ..., description="SHAP contribution for every feature, sorted by |SHAP|"
    )
    top_n: int = Field(..., description="Number of features in top_drivers")


class HealthResponse(BaseModel):
    status: str
    model_type: str
    shap_explainer_type: str


# ── Feature engineering (mirrors notebook exactly) ───────────────────────────
def nucleotide_features(seq: str) -> dict:
    seq = seq.upper()
    n = len(seq)
    feats: dict = {}
    for nt in ["A", "T", "G", "C"]:
        feats[f"guide_{nt}_freq"] = seq.count(nt) / n
    feats["guide_GC"] = (seq.count("G") + seq.count("C")) / n
    for d in [
        "AA", "AT", "AG", "AC",
        "TA", "TT", "TG", "TC",
        "GA", "GT", "GG", "GC",
        "CA", "CT", "CG", "CC",
    ]:
        feats[f"guide_di_{d}"] = (
            sum(1 for i in range(n - 1) if seq[i : i + 2] == d) / max(n - 1, 1)
        )
    feats["guide_seed_GC"] = (
        (seq[-12:].count("G") + seq[-12:].count("C")) / 12 if n >= 12 else 0
    )
    return feats


def amplicon_features(seq: str) -> dict:
    seq = str(seq).upper()
    n = len(seq)
    return {
        "amp_GC": (seq.count("G") + seq.count("C")) / max(n, 1),
        "amp_len": n,
    }


EXP_ORDER = {"low": 0, "medium": 1, "high": 2}
ALL_FEATURES = ["Exo", "Int", "Pro"]


def build_feature_vector(req: PredictionRequest) -> pd.DataFrame:
    row: dict = {}
    row["within_atac_peak"] = int(req.within_atac_peak)
    row["leaf_exp_enc"] = EXP_ORDER.get(req.leaf_exp, 1)
    row["t0_exp_enc"] = EXP_ORDER.get(req.t0_exp, 1)
    for feat in ALL_FEATURES:
        row[f"feat_{feat}"] = int(req.feature == feat)
    row.update(nucleotide_features(req.guide_sequence))
    row.update(amplicon_features(req.amplicon_sequence))

    df = pd.DataFrame([row])

    if hasattr(model, "feature_names_in_"):
        expected_cols = list(model.feature_names_in_)
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0
        df = df[expected_cols]

    return df


# ── Shared prediction + SHAP logic ───────────────────────────────────────────
def run_prediction(X: pd.DataFrame) -> tuple[float, bool]:
    raw = float(model.predict(X)[0])
    clipped = not (0.0 <= raw <= 100.0)
    return round(float(np.clip(raw, 0.0, 100.0)), 4), clipped

def run_shap(X: pd.DataFrame, top_n: int = 10) -> dict:
    shap_output = explainer(X)

    shap_values = shap_output.values[0]   # contributions
    base_value = float(shap_output.base_values[0])

    feature_vals = X.values[0]
    feature_names = list(X.columns)

    contributions = [
        FeatureContribution(
            feature=name,
            value=round(float(val), 6),
            shap_value=round(float(sv), 6),
            direction="up" if sv > 0 else "down",
        )
        for name, val, sv in zip(feature_names, feature_vals, shap_values)
    ]

    sorted_contribs = sorted(
        contributions, key=lambda c: abs(c.shap_value), reverse=True
    )

    return {
        "baseline": round(base_value, 4),
        "net_shap_shift": round(float(shap_values.sum()), 4),
        "top_drivers": sorted_contribs[:top_n],
        "all_contributions": sorted_contribs,
    }


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["Utility"])
def health():
    """Returns API status, model type, and SHAP explainer type."""
    return HealthResponse(
        status="ok",
        model_type=type(model).__name__,
        shap_explainer_type=type(explainer).__name__,
    )


@app.get("/features", tags=["Utility"])
def list_features():
    """Returns the feature names the model was trained on, if available."""
    if hasattr(model, "feature_names_in_"):
        return {"feature_names": list(model.feature_names_in_)}
    return {"feature_names": None, "note": "Model does not expose feature_names_in_"}


@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
def predict(req: PredictionRequest):
    """
    Predict CRISPR editing efficiency (%) for a given sgRNA.
    Fast — no SHAP. Use /explain if you need feature-level reasoning.
    """
    try:
        X = build_feature_vector(req)
        pred, clipped = run_prediction(X)
        return PredictionResponse(
            predicted_editing_efficiency=pred,
            prediction_clipped=clipped,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/explain", response_model=ExplainResponse, tags=["Prediction"])
def explain(req: PredictionRequest, top_n: int = 10):
    """
    Predict editing efficiency AND return a full SHAP explanation.

    - **baseline**: average model prediction across training data
    - **net_shap_shift**: how far this specific guide deviates from the baseline
    - **top_drivers**: the N features that moved the prediction the most
    - **all_contributions**: every feature's SHAP value, sorted by |SHAP|

    Pass `?top_n=15` to get more drivers (default is 10).
    """
    try:
        X = build_feature_vector(req)
        pred, clipped = run_prediction(X)
        shap_result = run_shap(X, top_n=top_n)

        return ExplainResponse(
            predicted_editing_efficiency=pred,
            prediction_clipped=clipped,
            top_n=top_n,
            **shap_result,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc