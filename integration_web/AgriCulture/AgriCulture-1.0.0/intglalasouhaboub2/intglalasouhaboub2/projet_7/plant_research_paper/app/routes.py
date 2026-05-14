from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.predictor import ResearchPredictor
from app.schemas import GenerateRequest, GenerateResponse, HealthResponse

router = APIRouter()
predictor = ResearchPredictor()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return predictor.health()


@router.post("/generate", response_model=GenerateResponse)
def generate_paper(request: GenerateRequest) -> GenerateResponse:
    try:
        return predictor.generate(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Paper generation failed: {exc}") from exc


@router.post("/generate/demo", response_model=GenerateResponse)
def generate_demo() -> GenerateResponse:
    try:
        return predictor.generate_demo()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Demo generation failed: {exc}") from exc


@router.get("/latest-results", response_model=GenerateResponse)
def latest_results() -> GenerateResponse:
    try:
        return predictor.latest()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to load latest report: {exc}") from exc
