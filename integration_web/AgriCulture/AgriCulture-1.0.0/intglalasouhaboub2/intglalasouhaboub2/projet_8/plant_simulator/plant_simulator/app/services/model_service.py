from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from data.dna_loader import DNARecord, load_dna_sequence
from ml.predict_growth import predict_growth_series
from ml.train_model import train


@dataclass(slots=True)
class TrainResult:
    mse_scaled: float
    model_path: str
    artifacts: dict[str, str]


def ensure_model(model_dir: Path, auto_train_if_missing: bool, epochs: int = 100) -> str:
    model_path = model_dir / "growth_model.pt"
    if model_path.exists():
        return "Model loaded from artifacts."
    if not auto_train_if_missing:
        raise FileNotFoundError("Model missing in artifacts/. Enable auto_train_if_missing or call /train first.")
    report = train(output_dir=model_dir, epochs=epochs)
    return f"Model auto-trained. Scaled MSE: {report['mse_scaled']:.4f}"


def train_model(model_dir: Path, epochs: int, batch_size: int, learning_rate: float) -> TrainResult:
    report = train(output_dir=model_dir, epochs=epochs, batch_size=batch_size, lr=learning_rate)
    return TrainResult(
        mse_scaled=float(report["mse_scaled"]),
        model_path=str(Path(report["model_path"]).resolve()),
        artifacts={
            "model": str((model_dir / "growth_model.pt").resolve()),
            "x_scaler": str((model_dir / "x_scaler.pkl").resolve()),
            "y_scaler": str((model_dir / "y_scaler.pkl").resolve()),
        },
    )


def load_dna(raw_sequence: str | None, accession: str | None) -> DNARecord:
    return load_dna_sequence(raw_sequence=raw_sequence, accession=accession)


def predict_growth(dna_sequence: str, climate: pd.DataFrame, model_dir: Path) -> pd.DataFrame:
    return predict_growth_series(dna_sequence=dna_sequence, climate_df=climate, model_dir=model_dir)
