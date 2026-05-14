from __future__ import annotations

import sqlite3
from collections import namedtuple
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple

import numpy as np


def namedtuple_factory(cursor: Any, row: Tuple[Any, ...]) -> Any:
    fields = [col[0] for col in cursor.description]
    Row = namedtuple("Row", fields)
    return Row(*row)


def open_db(db_path: str) -> sqlite3.Connection:
    p = Path(db_path)
    if not p.exists():
        raise FileNotFoundError(f"PCSE database not found: {p}")
    conn = sqlite3.connect(str(p))
    conn.row_factory = namedtuple_factory
    return conn


def normalize(val: float, col: str, ranges: Mapping[str, Tuple[float, float]]) -> float:
    if col not in ranges:
        return float(np.clip(val, 0.0, 1.0))
    mn, mx = ranges[col]
    if mx == mn:
        return 0.5
    return float(np.clip((val - mn) / (mx - mn), 0.0, 1.0))


def snp_to_wofost(row: Mapping[str, Any]) -> Dict[str, float]:
    """
    Map SNP_* signals (or trait-like proxies) to WOFOST parameters expected by the twin.
    If SNP columns are absent, falls back to pred_* values.
    """
    def _get(keys: Iterable[str], default: float) -> float:
        for k in keys:
            if k in row and row[k] is not None and not (isinstance(row[k], float) and np.isnan(row[k])):
                try:
                    return float(row[k])
                except Exception:
                    continue
        return float(default)

    pred_yield = _get(["pred_yield"], 0.75)
    pred_drought = _get(["pred_drought"], 0.60)
    pred_disease = _get(["pred_disease"], 0.70)

    # Light heuristic mapping to plausible WOFOST parameter ranges
    cfet = 0.9 + 0.2 * pred_yield  # 0.9..1.1
    depnr = 2.0 + 3.0 * (1.0 - pred_disease)  # 2..5
    tdwi = 40.0 + 30.0 * pred_yield  # 40..70
    span = 28.0 + 10.0 * pred_yield  # 28..38
    perdl = 0.01 + 0.04 * (1.0 - pred_drought)  # 0.01..0.05
    smfcf = 0.20 + 0.10 * pred_drought  # 0.20..0.30

    return {
        "CFET": float(cfet),
        "DEPNR": float(depnr),
        "TDWI": float(tdwi),
        "SPAN": float(span),
        "PERDL": float(perdl),
        "SMFCF": float(smfcf),
    }

