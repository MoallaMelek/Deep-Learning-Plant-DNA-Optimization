from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.schemas import ClimateManualInput
from data.climate_api import (
    ClimateConfig,
    TUNISIA_LATITUDE,
    TUNISIA_LONGITUDE,
    build_default_climate,
    fetch_open_meteo_climate,
)


@dataclass(slots=True)
class ClimateLoadResult:
    frame: pd.DataFrame
    source: str
    warnings: list[str]


def build_manual_climate(days: int, manual: ClimateManualInput) -> pd.DataFrame:
    cfg = ClimateConfig(
        latitude=TUNISIA_LATITUDE,
        longitude=TUNISIA_LONGITUDE,
        days=days,
        temperature_c=manual.temperature_c,
        humidity_pct=manual.humidity_pct,
        precipitation_mm=manual.precipitation_mm,
        sunlight_hours=manual.sunlight_hours,
        wind_kph=manual.wind_kph,
    )
    return build_default_climate(days=days, config=cfg)


def load_climate(days: int, use_open_meteo: bool, manual: ClimateManualInput) -> ClimateLoadResult:
    warnings: list[str] = []
    if use_open_meteo:
        try:
            climate = fetch_open_meteo_climate(
                latitude=TUNISIA_LATITUDE,
                longitude=TUNISIA_LONGITUDE,
                days=days,
            )
            return ClimateLoadResult(frame=climate, source="Open-Meteo API (Tunisia)", warnings=warnings)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"Open-Meteo unavailable, fallback to manual synthetic climate: {exc}")

    manual_frame = build_manual_climate(days=days, manual=manual)
    return ClimateLoadResult(frame=manual_frame, source="Manual synthetic climate", warnings=warnings)
