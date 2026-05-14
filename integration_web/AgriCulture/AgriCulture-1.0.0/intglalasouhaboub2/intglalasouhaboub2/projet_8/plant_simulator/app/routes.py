from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.predictor import PlantSimulatorPredictor
from app.schemas import (
    HealthResponse,
    PredictGrowthRequest,
    PredictGrowthResponse,
    SimulateRequest,
    SimulateResponse,
    TrainRequest,
    TrainResponse,
)

router = APIRouter()
predictor = PlantSimulatorPredictor()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return predictor.health()


@router.post("/predict-growth", response_model=PredictGrowthResponse)
def predict_growth(request: PredictGrowthRequest) -> PredictGrowthResponse:
    try:
        return predictor.predict(request)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc


@router.post("/train", response_model=TrainResponse)
def train_model(request: TrainRequest) -> TrainResponse:
    try:
        return predictor.train(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Training failed: {exc}") from exc


@router.post("/simulate", response_model=SimulateResponse)
def simulate_growth(request: SimulateRequest) -> SimulateResponse:
    try:
        return predictor.simulate(request)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}") from exc
