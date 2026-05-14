import re
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from app.config import CNN_COLS, DATA_PATH, TARGET_COLS


def resolve_existing_path(preferred: Path, fallback_name: str) -> Path:
    if preferred.exists():
        return preferred
    fallback = preferred.parent.parent / fallback_name
    if fallback.exists():
        return fallback
    raise FileNotFoundError(f"File not found: {preferred} or {fallback}")


def load_raw_dataset() -> pd.DataFrame:
    data_path = resolve_existing_path(DATA_PATH, "finalfinal.csv")
    return pd.read_csv(data_path, sep=";")


def preprocess_dataset(df: pd.DataFrame) -> pd.DataFrame:
    snp_cols = [c for c in df.columns if c.startswith("SNP")]
    agg = {c: "mean" for c in TARGET_COLS + CNN_COLS if c in df.columns}
    agg.update({c: (lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0]) for c in snp_cols})
    out = df.groupby("variety_name", as_index=False).agg(agg)
    out = out[~out["variety_name"].astype(str).str.fullmatch(r"\d+")].copy()
    for col in snp_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0).astype(float)
    return out


def find_variety_row(df: pd.DataFrame, variety_name: str) -> pd.Series:
    mask = df["variety_name"].astype(str).str.contains(re.escape(variety_name), case=False, na=False)
    if not mask.any():
        raise KeyError(variety_name)
    return df.loc[mask].iloc[0]


def normalize_weights(w: Dict[str, float]) -> Dict[str, float]:
    vals = np.array([w["drought"], w["salt"], w["yield"], w["disease"]], dtype=float)
    s = vals.sum()
    if s <= 0:
        vals = np.ones_like(vals) / 4.0
    else:
        vals = vals / s
    return {"drought": float(vals[0]), "salt": float(vals[1]), "yield": float(vals[2]), "disease": float(vals[3])}


def wrap_fasta(seq: str, width: int = 60) -> str:
    return "\n".join(seq[i : i + width] for i in range(0, len(seq), width))
