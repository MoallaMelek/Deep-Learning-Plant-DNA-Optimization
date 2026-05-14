"""Inference helpers for day-by-day plant growth prediction."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch

from ml.dna_encoder import build_dna_feature_vector
from ml.model import load_model
from ml.train_model import TARGET_COLUMNS


def _prepare_feature_matrix(dna_sequence: str, climate_df: pd.DataFrame) -> np.ndarray:
    dna_features = build_dna_feature_vector(dna_sequence)
    rows = []
    n_days = len(climate_df)
    for idx, row in climate_df.reset_index(drop=True).iterrows():
        day_norm = idx / max(1, n_days - 1)
        climate_vec = np.array(
            [
                row["temperature_c"],
                row["humidity_pct"],
                row["precipitation_mm"],
                row["sunlight_hours"],
                row["wind_kph"],
            ],
            dtype=np.float32,
        )
        rows.append(np.concatenate([dna_features, climate_vec, np.array([day_norm], dtype=np.float32)]))
    return np.array(rows, dtype=np.float32)


def predict_growth_series(dna_sequence: str, climate_df: pd.DataFrame, model_dir: Path) -> pd.DataFrame:
    model, metadata = load_model(model_dir / "growth_model.pt")
    x_scaler = joblib.load(model_dir / "x_scaler.pkl")
    y_scaler = joblib.load(model_dir / "y_scaler.pkl")

    features = _prepare_feature_matrix(dna_sequence, climate_df)
    Xs = x_scaler.transform(features).astype(np.float32)

    with torch.no_grad():
        preds_scaled = model(torch.from_numpy(Xs)).cpu().numpy()
    preds = y_scaler.inverse_transform(preds_scaled)

    out = pd.DataFrame(preds, columns=metadata.get("target_columns", TARGET_COLUMNS))
    out["height_cm"] = np.maximum.accumulate(np.clip(out["height_cm"].to_numpy(), 0.1, None))
    out["leaf_count"] = np.clip(np.round(out["leaf_count"]), 1, None)
    out["leaf_size_cm2"] = np.clip(out["leaf_size_cm2"], 0.2, None)
    out["stem_thickness_mm"] = np.clip(out["stem_thickness_mm"], 0.4, None)
    out["branch_count"] = np.clip(np.round(out["branch_count"]), 0, None)
    out["health_index"] = np.clip(out["health_index"], 0, 1)
    out["growth_rate_cm_day"] = np.clip(out["growth_rate_cm_day"], 0.01, None)
    out["day_index"] = np.arange(len(out))
    out["date"] = pd.to_datetime(climate_df["date"]).astype(str).to_list()
    return out
