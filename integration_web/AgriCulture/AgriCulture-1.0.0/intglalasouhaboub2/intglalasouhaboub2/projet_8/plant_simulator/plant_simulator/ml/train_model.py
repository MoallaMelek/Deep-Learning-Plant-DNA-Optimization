"""Training pipeline for a CPU-friendly plant growth predictor."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

from data.climate_api import build_default_climate
from ml.dna_encoder import build_dna_feature_vector
from ml.model import PlantGrowthNet, get_cpu_device, save_model

TARGET_COLUMNS = [
    "height_cm",
    "leaf_count",
    "leaf_size_cm2",
    "stem_thickness_mm",
    "branch_count",
    "health_index",
    "growth_rate_cm_day",
]


def _random_dna(rng: np.random.Generator, min_len: int = 250, max_len: int = 1500) -> str:
    n = int(rng.integers(min_len, max_len + 1))
    return "".join(rng.choice(list("ACGT"), size=n))


def _simulate_targets(
    dna_seq: str, climate_df: pd.DataFrame, vigor_jitter: float, rng: np.random.Generator
) -> pd.DataFrame:
    dna_feat = build_dna_feature_vector(dna_seq)
    gc = float(dna_feat[4])
    composition_bonus = float(dna_feat[0] * 0.05 + dna_feat[2] * 0.08)
    vigor = 0.7 + 0.9 * gc + composition_bonus + vigor_jitter

    rows = []
    height = 0.0
    for day, row in climate_df.reset_index(drop=True).iterrows():
        temp = float(row["temperature_c"])
        humidity = float(row["humidity_pct"])
        precip = float(row["precipitation_mm"])
        sun = float(row["sunlight_hours"])
        wind = float(row["wind_kph"])

        temp_factor = np.exp(-((temp - 24.0) / 11.0) ** 2)
        humidity_factor = np.exp(-((humidity - 65.0) / 28.0) ** 2)
        water_factor = 1.0 - np.exp(-precip / 7.0)
        light_factor = np.clip(sun / 9.0, 0.3, 1.4)
        wind_penalty = np.clip(1.0 - wind / 75.0, 0.4, 1.0)

        raw_growth = (
            1.8
            * vigor
            * temp_factor
            * (0.6 + 0.4 * humidity_factor)
            * (0.45 + 0.55 * water_factor)
            * light_factor
            * wind_penalty
        )
        growth_rate = max(0.05, raw_growth + rng.normal(0, 0.07))
        height += growth_rate

        leaf_count = max(1.0, 2.0 + day * (0.35 + 0.2 * vigor) + rng.normal(0, 0.6))
        leaf_size = max(0.3, 1.0 + 0.09 * height + 0.2 * light_factor + rng.normal(0, 0.12))
        stem_thickness = max(0.6, 1.2 + 0.08 * height + 0.4 * wind_penalty + rng.normal(0, 0.08))
        branch_count = max(0.0, (height - 15) / 6.5 + rng.normal(0, 0.4))
        health = np.clip(
            0.45
            + 0.35 * temp_factor
            + 0.25 * humidity_factor
            + 0.15 * light_factor
            - 0.09 * (wind / 30.0)
            + rng.normal(0, 0.03),
            0.0,
            1.0,
        )

        rows.append(
            {
                "height_cm": height,
                "leaf_count": leaf_count,
                "leaf_size_cm2": leaf_size,
                "stem_thickness_mm": stem_thickness,
                "branch_count": branch_count,
                "health_index": health,
                "growth_rate_cm_day": growth_rate,
            }
        )
    return pd.DataFrame(rows)


def generate_synthetic_dataset(
    n_plants: int = 220, days: int = 90, random_seed: int = 7
) -> Tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(random_seed)
    feature_rows = []
    target_rows = []

    for _ in range(n_plants):
        dna = _random_dna(rng)
        climate = build_default_climate(days=days)
        climate["temperature_c"] += rng.normal(0, 3.0, size=len(climate))
        climate["humidity_pct"] = np.clip(climate["humidity_pct"] + rng.normal(0, 4.0, size=len(climate)), 20, 98)
        climate["sunlight_hours"] = np.clip(
            climate["sunlight_hours"] + rng.normal(0, 0.8, size=len(climate)), 1.0, 14.0
        )
        climate["wind_kph"] = np.clip(climate["wind_kph"] + rng.normal(0, 2.0, size=len(climate)), 0.2, 60.0)
        climate["precipitation_mm"] = np.clip(
            climate["precipitation_mm"] + rng.normal(0, 1.2, size=len(climate)), 0.0, 40.0
        )

        targets = _simulate_targets(dna, climate, vigor_jitter=rng.normal(0, 0.08), rng=rng)
        dna_features = build_dna_feature_vector(dna)

        for day_idx, climate_row in climate.reset_index(drop=True).iterrows():
            day_norm = day_idx / max(1, days - 1)
            climate_vec = np.array(
                [
                    climate_row["temperature_c"],
                    climate_row["humidity_pct"],
                    climate_row["precipitation_mm"],
                    climate_row["sunlight_hours"],
                    climate_row["wind_kph"],
                ],
                dtype=np.float32,
            )
            x = np.concatenate([dna_features, climate_vec, np.array([day_norm], dtype=np.float32)], axis=0)
            y = targets.iloc[day_idx][TARGET_COLUMNS].to_numpy(dtype=np.float32)
            feature_rows.append(x)
            target_rows.append(y)

    return np.array(feature_rows, dtype=np.float32), np.array(target_rows, dtype=np.float32)


def train(output_dir: Path, epochs: int = 120, batch_size: int = 256, lr: float = 1e-3) -> dict:
    torch.set_num_threads(max(1, (os.cpu_count() or 2) - 1))
    device = get_cpu_device()

    X, y = generate_synthetic_dataset()
    x_scaler = StandardScaler()
    y_scaler = StandardScaler()
    Xs = x_scaler.fit_transform(X).astype(np.float32)
    ys = y_scaler.fit_transform(y).astype(np.float32)

    X_train, X_test, y_train, y_test = train_test_split(Xs, ys, test_size=0.15, random_state=42)

    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train)),
        batch_size=batch_size,
        shuffle=True,
    )

    model = PlantGrowthNet(input_dim=X.shape[1], output_dim=y.shape[1]).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    for _ in range(epochs):
        model.train()
        for xb, yb in train_loader:
            xb = xb.to(device)
            yb = yb.to(device)
            optimizer.zero_grad(set_to_none=True)
            preds = model(xb)
            loss = criterion(preds, yb)
            loss.backward()
            optimizer.step()

    model.eval()
    with torch.no_grad():
        test_preds = model(torch.from_numpy(X_test).to(device)).cpu().numpy()
    mse = float(mean_squared_error(y_test, test_preds))

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "growth_model.pt"
    save_model(
        model,
        model_path,
        metadata={"input_dim": X.shape[1], "output_dim": y.shape[1], "target_columns": TARGET_COLUMNS},
    )
    joblib.dump(x_scaler, output_dir / "x_scaler.pkl")
    joblib.dump(y_scaler, output_dir / "y_scaler.pkl")

    return {"mse_scaled": mse, "model_path": str(model_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the plant growth prediction model.")
    parser.add_argument("--output-dir", default="artifacts", help="Directory where model artifacts are written.")
    parser.add_argument("--epochs", type=int, default=120)
    args = parser.parse_args()

    report = train(output_dir=Path(args.output_dir), epochs=args.epochs)
    print(f"Training completed. Scaled test MSE={report['mse_scaled']:.4f}")
    print(f"Model saved to: {report['model_path']}")


if __name__ == "__main__":
    main()
