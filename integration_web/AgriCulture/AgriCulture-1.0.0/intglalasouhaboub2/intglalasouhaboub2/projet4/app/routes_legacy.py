from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.config import HORIZONS, SCENARIOS
from app.models.wheat import PredictRequest, RecommendRequest, SimulateRequest
from app.predictor import DigitalTwinPredictor


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _http_500(message: str, err: Exception) -> HTTPException:
    return HTTPException(status_code=500, detail={"error": message, "details": str(err)})


@router.get("/health")
def health() -> Dict[str, Any]:
    try:
        p = DigitalTwinPredictor()
        return p.get_health()
    except Exception as e:
        raise _http_500("health_check_failed", e)


@router.get("/norms")
def norms() -> Dict[str, Any]:
    try:
        p = DigitalTwinPredictor()
        return p.get_norms()
    except Exception as e:
        raise _http_500("norms_failed", e)


@router.post("/predict")
def predict(req: PredictRequest) -> Dict[str, Any]:
    try:
        p = DigitalTwinPredictor()
        return p.predict(req.row.model_dump())
    except RuntimeError:
        raise HTTPException(status_code=503, detail={"error": "WOFOST unavailable"})
    except Exception as e:
        raise _http_500("predict_failed", e)


@router.post("/recommend")
def recommend(req: RecommendRequest) -> Dict[str, Any]:
    try:
        p = DigitalTwinPredictor()
        traits = req.traits.model_dump() if req.traits else None
        return p.recommend(req.variety_name, traits, req.horizon, req.scenario)
    except KeyError as e:
        raise HTTPException(status_code=404, detail={"error": str(e)})
    except Exception as e:
        raise _http_500("recommend_failed", e)


@router.post("/simulate")
def simulate(req: SimulateRequest) -> Dict[str, Any]:
    try:
        p = DigitalTwinPredictor()
        return p.simulate(req.row.model_dump(), req.n_jours, req.scenario)
    except Exception as e:
        raise _http_500("simulate_failed", e)


@router.get("/viz", response_class=HTMLResponse)
def viz(
    request: Request,
    variety_name: Optional[str] = None,
    yield_score: float = 0.75,
    drought_score: float = 0.60,
    disease_score: float = 0.70,
    scenario: str = "normal",
    horizon: str = "6_mois",
) -> HTMLResponse:
    try:
        if scenario not in SCENARIOS:
            scenario = "normal"
        if horizon not in HORIZONS:
            horizon = "6_mois"

        p = DigitalTwinPredictor()
        viz_data = p.get_viz_data(
            {
                "variety_name": variety_name,
                "yield_score": yield_score,
                "drought_score": drought_score,
                "disease_score": disease_score,
                "scenario": scenario,
                "horizon": horizon,
            }
        )
        return templates.TemplateResponse("viz.html", {"request": request, "data": viz_data})
    except KeyError as e:
        raise HTTPException(status_code=404, detail={"error": str(e)})
    except Exception as e:
        raise _http_500("viz_failed", e)


@router.get("/viz/data")
def viz_data(
    variety_name: Optional[str] = None,
    yield_score: float = 0.75,
    drought_score: float = 0.60,
    disease_score: float = 0.70,
    scenario: str = "normal",
    horizon: str = "6_mois",
) -> JSONResponse:
    try:
        if scenario not in SCENARIOS:
            scenario = "normal"
        if horizon not in HORIZONS:
            horizon = "6_mois"
        p = DigitalTwinPredictor()
        data = p.get_viz_data(
            {
                "variety_name": variety_name,
                "yield_score": yield_score,
                "drought_score": drought_score,
                "disease_score": disease_score,
                "scenario": scenario,
                "horizon": horizon,
            }
        )
        return JSONResponse(data)
    except KeyError as e:
        raise HTTPException(status_code=404, detail={"error": str(e)})
    except Exception as e:
        raise _http_500("viz_data_failed", e)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, n_jours: int = 200) -> HTMLResponse:
    try:
        p = DigitalTwinPredictor()
        data = p.get_dashboard_payload(n_jours=n_jours)
        return templates.TemplateResponse("dashboard.html", {"request": request, "data": data})
    except Exception as e:
        raise _http_500("dashboard_failed", e)


@router.get("/dashboard/data")
def dashboard_data(n_jours: int = 200) -> JSONResponse:
    try:
        p = DigitalTwinPredictor()
        return JSONResponse(p.get_dashboard_payload(n_jours=n_jours))
    except Exception as e:
        raise _http_500("dashboard_data_failed", e)

