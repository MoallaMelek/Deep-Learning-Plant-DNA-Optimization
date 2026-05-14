from __future__ import annotations

import datetime as dt
from pathlib import Path

from app.config import settings
from app.schemas import (
    AssetUrls,
    HealthResponse,
    PredictGrowthRequest,
    PredictGrowthResponse,
    PredictionDay,
    SimulateRequest,
    SimulateResponse,
    TrainRequest,
    TrainResponse,
)
from app.services.climate_service import load_climate
from app.services.model_service import ensure_model, load_dna, predict_growth, train_model
from app.services.visualization_service import generate_growth_gif, generate_predictions_chart


class PlantSimulatorPredictor:
    def __init__(self) -> None:
        self.artifacts_dir = settings.artifacts_dir
        self.outputs_dir = settings.outputs_dir
        self.media_dir = settings.media_dir

    def health(self) -> HealthResponse:
        model_available = (self.artifacts_dir / "growth_model.pt").exists()
        status = "ok" if model_available else "degraded"
        return HealthResponse(
            status=status,
            version=settings.app_version,
            artifacts_dir=str(self.artifacts_dir.resolve()),
            outputs_dir=str(self.outputs_dir.resolve()),
            model_available=model_available,
        )

    def train(self, request: TrainRequest) -> TrainResponse:
        report = train_model(
            model_dir=self.artifacts_dir,
            epochs=request.epochs,
            batch_size=request.batch_size,
            learning_rate=request.learning_rate,
        )
        return TrainResponse(
            message="Training completed successfully.",
            mse_scaled=report.mse_scaled,
            model_path=report.model_path,
            artifacts=report.artifacts,
        )

    def predict(self, request: PredictGrowthRequest) -> PredictGrowthResponse:
        warnings: list[str] = []
        dna_record = load_dna(raw_sequence=request.dna_sequence, accession=request.accession)
        model_status = ensure_model(self.artifacts_dir, auto_train_if_missing=request.auto_train_if_missing)
        climate_result = load_climate(
            days=request.days,
            use_open_meteo=request.use_open_meteo,
            manual=request.manual_climate,
        )
        warnings.extend(climate_result.warnings)

        predictions = predict_growth(dna_sequence=dna_record.sequence, climate=climate_result.frame, model_dir=self.artifacts_dir)

        chart_path = None
        chart_base64 = None
        if request.generate_chart:
            run_dir = self._new_run_dir()
            chart_path, chart_base64 = generate_predictions_chart(
                predictions=predictions,
                output_dir=run_dir,
                as_base64=request.chart_as_base64,
            )

        day_rows = [
            PredictionDay(
                day_index=int(row["day_index"]),
                date=str(row["date"]),
                height_cm=float(row["height_cm"]),
                leaf_count=int(row["leaf_count"]),
                leaf_size_cm2=float(row["leaf_size_cm2"]),
                stem_thickness_mm=float(row["stem_thickness_mm"]),
                branch_count=int(row["branch_count"]),
                health_index=float(row["health_index"]),
                growth_rate_cm_day=float(row["growth_rate_cm_day"]),
            )
            for row in predictions.to_dict(orient="records")
        ]
        last = day_rows[-1]

        return PredictGrowthResponse(
            dna_source=dna_record.source,
            climate_source=climate_result.source,
            model_status=model_status,
            predictions=day_rows,
            summary={
                "final_height_cm": round(last.height_cm, 2),
                "final_leaf_count": int(last.leaf_count),
                "final_branch_count": int(last.branch_count),
                "final_health": round(last.health_index, 4),
            },
            chart_path=chart_path,
            chart_base64=chart_base64,
            asset_urls=self._build_asset_urls(chart_path=chart_path),
            warnings=warnings,
        )

    def simulate(self, request: SimulateRequest) -> SimulateResponse:
        prediction_response = self.predict(request)
        warnings = list(prediction_response.warnings)
        gif_path = None
        metadata: dict[str, str | int] = {"requested_days": request.days}

        if request.generate_gif:
            try:
                # Re-run dataframe build from API-ready rows to keep simulate independent.
                import pandas as pd

                prediction_df = pd.DataFrame([row.model_dump() for row in prediction_response.predictions])
                gif_path = generate_growth_gif(
                    predictions=prediction_df,
                    media_dir=self.media_dir,
                    filename=request.gif_filename,
                )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"GIF generation failed: {exc}")

        return SimulateResponse(
            dna_source=prediction_response.dna_source,
            climate_source=prediction_response.climate_source,
            model_status=prediction_response.model_status,
            predictions=prediction_response.predictions,
            summary=prediction_response.summary,
            chart_path=prediction_response.chart_path,
            chart_base64=prediction_response.chart_base64,
            asset_urls=self._build_asset_urls(
                chart_path=prediction_response.chart_path,
                gif_path=gif_path,
            ),
            warnings=warnings,
            gif_path=gif_path,
            metadata=metadata,
        )

    def _new_run_dir(self) -> Path:
        run_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.outputs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _build_asset_urls(self, chart_path: str | None = None, gif_path: str | None = None) -> AssetUrls:
        return AssetUrls(
            chart=self._resolve_asset_url(chart_path, self.outputs_dir, "/growth/outputs"),
            gif=self._resolve_asset_url(gif_path, self.media_dir, "/growth/media"),
        )

    def _resolve_asset_url(self, path_value: str | None, root_dir: Path, prefix: str) -> str | None:
        if not path_value:
            return None

        raw_path = Path(str(path_value).replace("\\", "/"))
        resolved_root = root_dir.resolve()

        if raw_path.is_absolute():
            try:
                relative = raw_path.resolve().relative_to(resolved_root)
            except ValueError:
                parts = raw_path.parts
                root_name = root_dir.name
                if root_name not in parts:
                    return None
                relative = Path(*parts[parts.index(root_name) + 1 :])
        else:
            parts = raw_path.parts
            relative = Path(*parts[1:]) if parts and parts[0] == root_dir.name else raw_path

        relative_url = "/".join(part for part in relative.parts if part not in {"", "."})
        return f"{prefix}/{relative_url}" if relative_url else None
