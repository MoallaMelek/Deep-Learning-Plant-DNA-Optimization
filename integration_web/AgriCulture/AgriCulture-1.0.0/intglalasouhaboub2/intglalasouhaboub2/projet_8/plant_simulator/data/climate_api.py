"""Climate data retrieval and preparation using Open-Meteo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import requests

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TUNISIA_LATITUDE = 36.8065
TUNISIA_LONGITUDE = 10.1815


@dataclass
class ClimateConfig:
    latitude: float
    longitude: float
    days: int
    temperature_c: float = 22.0
    humidity_pct: float = 60.0
    precipitation_mm: float = 1.5
    sunlight_hours: float = 8.0
    wind_kph: float = 10.0


def build_default_climate(days: int, config: Optional[ClimateConfig] = None) -> pd.DataFrame:
    """Create synthetic climate values when online data is unavailable."""
    cfg = config or ClimateConfig(latitude=48.8566, longitude=2.3522, days=days)
    start = date.today()
    rng = np.random.default_rng(42)
    rows = []
    for d in range(days):
        seasonal = np.sin((2 * np.pi * d) / max(14, days))
        rows.append(
            {
                "date": start + timedelta(days=d),
                "temperature_c": cfg.temperature_c + 4.5 * seasonal + rng.normal(0, 0.8),
                "humidity_pct": np.clip(cfg.humidity_pct - 7.0 * seasonal + rng.normal(0, 2.0), 25, 95),
                "precipitation_mm": max(0.0, cfg.precipitation_mm + rng.normal(0, 0.6)),
                "sunlight_hours": np.clip(cfg.sunlight_hours + 1.5 * seasonal + rng.normal(0, 0.4), 2, 14),
                "wind_kph": np.clip(cfg.wind_kph + rng.normal(0, 1.5), 0.5, 45),
            }
        )
    return pd.DataFrame(rows)


def _daily_humidity_from_hourly(hourly: dict) -> pd.DataFrame:
    """Aggregate hourly relative humidity to daily mean."""
    times = pd.to_datetime(hourly["time"])
    humidity = np.array(hourly["relative_humidity_2m"], dtype=float)
    frame = pd.DataFrame({"datetime": times, "humidity_pct": humidity})
    frame["date"] = frame["datetime"].dt.date
    out = frame.groupby("date", as_index=False)["humidity_pct"].mean()
    return out


def fetch_open_meteo_climate(latitude: float, longitude: float, days: int) -> pd.DataFrame:
    """Fetch climate forecast from Open-Meteo and return normalized daily features."""
    if days < 1:
        raise ValueError("days must be >= 1")
    # Force Open-Meteo requests to Tunisia climate regardless of caller-provided coordinates.
    latitude = TUNISIA_LATITUDE
    longitude = TUNISIA_LONGITUDE
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,sunshine_duration,wind_speed_10m_max",
        "hourly": "relative_humidity_2m",
        "forecast_days": int(days),
        "timezone": "auto",
    }
    response = requests.get(OPEN_METEO_FORECAST_URL, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()
    daily = payload["daily"]

    out = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]).date,
            "temperature_c": (np.array(daily["temperature_2m_max"]) + np.array(daily["temperature_2m_min"])) / 2.0,
            "precipitation_mm": np.array(daily["precipitation_sum"], dtype=float),
            "sunlight_hours": np.array(daily["sunshine_duration"], dtype=float) / 3600.0,
            "wind_kph": np.array(daily["wind_speed_10m_max"], dtype=float),
        }
    )

    humidity = _daily_humidity_from_hourly(payload["hourly"])
    out = out.merge(humidity, on="date", how="left")
    out["humidity_pct"] = out["humidity_pct"].interpolate().bfill().ffill().clip(0, 100)
    return normalize_climate_frame(out)


def normalize_climate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Clamp climate ranges and return canonical columns."""
    required = ["date", "temperature_c", "humidity_pct", "precipitation_mm", "sunlight_hours", "wind_kph"]
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError(f"Climate frame is missing columns: {missing}")

    out = frame.copy()
    out["temperature_c"] = out["temperature_c"].astype(float).clip(-20, 50)
    out["humidity_pct"] = out["humidity_pct"].astype(float).clip(0, 100)
    out["precipitation_mm"] = out["precipitation_mm"].astype(float).clip(0, 300)
    out["sunlight_hours"] = out["sunlight_hours"].astype(float).clip(0, 24)
    out["wind_kph"] = out["wind_kph"].astype(float).clip(0, 200)
    out["date"] = pd.to_datetime(out["date"]).dt.date
    return out[required]
