from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str
    artifacts_dir: str
    outputs_dir: str
    model_available: bool


class ClimateManualInput(BaseModel):
    temperature_c: float = Field(default=22.0)
    humidity_pct: float = Field(default=60.0)
    precipitation_mm: float = Field(default=1.5)
    sunlight_hours: float = Field(default=8.0)
    wind_kph: float = Field(default=10.0)


class PredictGrowthRequest(BaseModel):
    dna_sequence: str | None = Field(default=None, description="Raw DNA sequence.")
    accession: str | None = Field(default=None, description="NCBI accession (optional).")
    days: int = Field(default=60, ge=1, le=365)
    use_open_meteo: bool = Field(default=True)
    manual_climate: ClimateManualInput = Field(default_factory=ClimateManualInput)
    auto_train_if_missing: bool = Field(default=True)
    generate_chart: bool = Field(default=True)
    chart_as_base64: bool = Field(default=False)


class TrainRequest(BaseModel):
    epochs: int = Field(default=120, ge=1, le=2000)
    batch_size: int = Field(default=256, ge=8, le=4096)
    learning_rate: float = Field(default=1e-3, gt=0, le=1)


class PredictionDay(BaseModel):
    day_index: int
    date: str
    height_cm: float
    leaf_count: int
    leaf_size_cm2: float
    stem_thickness_mm: float
    branch_count: int
    health_index: float
    growth_rate_cm_day: float


class GrowthSummary(BaseModel):
    final_height_cm: float
    final_leaf_count: int
    final_branch_count: int
    final_health: float


class AssetUrls(BaseModel):
    chart: str | None = None
    gif: str | None = None


class PredictGrowthResponse(BaseModel):
    dna_source: str
    climate_source: str
    model_status: str
    predictions: list[PredictionDay]
    summary: GrowthSummary
    chart_path: str | None = None
    chart_base64: str | None = None
    asset_urls: AssetUrls | None = None
    warnings: list[str] = Field(default_factory=list)


class TrainResponse(BaseModel):
    message: str
    mse_scaled: float
    model_path: str
    artifacts: dict[str, str]


class SimulateRequest(PredictGrowthRequest):
    generate_gif: bool = Field(default=True)
    gif_filename: str = Field(default="latest_growth.gif")


class SimulateResponse(PredictGrowthResponse):
    gif_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
