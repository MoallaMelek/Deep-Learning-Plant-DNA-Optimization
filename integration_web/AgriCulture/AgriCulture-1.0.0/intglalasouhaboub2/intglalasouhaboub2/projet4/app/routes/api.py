from __future__ import annotations

import base64
from io import BytesIO
from typing import Any, Dict, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

from app.config import HORIZONS, SCENARIOS
from app.models.wheat import PredictRequest, RecommendRequest, SimulateRequest
from app.services.digital_twin_service import DigitalTwinService


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _http_500(message: str, err: Exception) -> HTTPException:
    return HTTPException(status_code=500, detail={"error": message, "details": str(err)})


def _build_3d_image(data: Dict[str, Any]) -> str:
    growth = min(max(float(data.get("horizonDays", 180)) / 180.0, 0.1), 1.0)
    risk = float(data.get("stressRisks", {}).get("overall", 0.3))
    twso = float(data.get("twso", 0.0))

    x = np.linspace(-2, 2, 40)
    y = np.linspace(-2, 2, 40)
    X, Y = np.meshgrid(x, y)
    Z = growth * np.exp(-(X**2 + Y**2) / 2.0) * (1.0 - 0.6 * risk)

    fig = plt.figure(figsize=(7, 4.5), dpi=120)
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(X, Y, Z, cmap="YlGn", edgecolor="none", alpha=0.95)
    ax.set_title(f"3D Crop Surface - TWSO {twso:.0f} kg/ha")
    ax.set_xlabel("Field X")
    ax.set_ylabel("Field Y")
    ax.set_zlabel("Biomass")
    ax.view_init(elev=28, azim=225)

    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


@router.get("/")
def root() -> Dict[str, Any]:
    try:
        return DigitalTwinService().root_payload()
    except Exception as e:
        raise _http_500("root_failed", e)


@router.get("/health")
def health() -> Dict[str, Any]:
    try:
        return DigitalTwinService().health()
    except Exception as e:
        raise _http_500("health_check_failed", e)


@router.get("/norms")
def norms() -> Dict[str, Any]:
    try:
        return DigitalTwinService().norms()
    except Exception as e:
        raise _http_500("norms_failed", e)


@router.post("/predict")
def predict(req: PredictRequest) -> Dict[str, Any]:
    try:
        return DigitalTwinService().predict(req.row.model_dump())
    except Exception as e:
        raise _http_500("predict_failed", e)


@router.post("/recommend")
def recommend(req: Optional[RecommendRequest] = None) -> Dict[str, Any]:
    try:
        if req is None:
            return DigitalTwinService().recommend(
                variety_name=None,
                traits={"pred_yield": 0.75, "pred_drought": 0.60, "pred_disease": 0.70, "pred_salt": 0.50},
                horizon="6_mois",
                scenario="normal",
            )
        traits = req.traits.model_dump() if req.traits else None
        return DigitalTwinService().recommend(req.variety_name, traits, req.horizon, req.scenario)
    except KeyError as e:
        raise HTTPException(status_code=404, detail={"error": str(e)})
    except Exception as e:
        raise _http_500("recommend_failed", e)


@router.get("/recommend")
def recommend_get(
    variety_name: Optional[str] = None,
    yield_score: Optional[float] = None,
    drought_score: Optional[float] = None,
    disease_score: Optional[float] = None,
    salt_score: Optional[float] = None,
    horizon: str = "6_mois",
    scenario: str = "normal",
) -> Dict[str, Any]:
    try:
        if scenario not in SCENARIOS:
            scenario = "normal"
        if horizon not in HORIZONS:
            horizon = "6_mois"
        traits = None
        if not variety_name:
            traits = {
                "pred_yield": 0.75 if yield_score is None else float(yield_score),
                "pred_drought": 0.60 if drought_score is None else float(drought_score),
                "pred_disease": 0.70 if disease_score is None else float(disease_score),
                "pred_salt": 0.50 if salt_score is None else float(salt_score),
            }
        return DigitalTwinService().recommend(variety_name, traits, horizon, scenario)
    except KeyError as e:
        raise HTTPException(status_code=404, detail={"error": str(e)})
    except Exception as e:
        raise _http_500("recommend_get_failed", e)


@router.post("/simulate")
def simulate(req: SimulateRequest) -> Dict[str, Any]:
    try:
        return DigitalTwinService().simulate(req.row.model_dump(), req.n_jours, req.scenario)
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

        viz_data = DigitalTwinService().viz_data(
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
        data = DigitalTwinService().viz_data(
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


@router.get("/viz/3d", response_class=HTMLResponse)
def viz_3d(
    variety_name: Optional[str] = None,
    yield_score: float = 0.75,
    drought_score: float = 0.60,
    disease_score: float = 0.70,
    scenario: str = "normal",
    horizon: str = "6_mois",
) -> HTMLResponse:
    try:
        data = DigitalTwinService().viz_data(
            {
                "variety_name": variety_name,
                "yield_score": yield_score,
                "drought_score": drought_score,
                "disease_score": disease_score,
                "scenario": scenario,
                "horizon": horizon,
            }
        )
        img_b64 = _build_3d_image(data)
        html = f"""
        <html><head><meta charset=\"utf-8\"><title>3D Visualization</title></head>
        <body style=\"font-family:Arial,sans-serif;background:#f6f8fa;margin:0;padding:24px;\">
          <h2>Digital Twin 3D Visualization</h2>
          <p>Scenario: {data.get('scenario')} | Horizon: {data.get('horizonDays')} days | TWSO: {data.get('twso'):.0f} kg/ha</p>
          <img alt=\"3D crop visualization\" style=\"max-width:100%;border:1px solid #ddd;border-radius:8px;\" src=\"data:image/png;base64,{img_b64}\" />
        </body></html>
        """
        return HTMLResponse(content=html)
    except Exception as e:
        raise _http_500("viz_3d_failed", e)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, n_jours: int = 200) -> HTMLResponse:
    try:
        data = DigitalTwinService().dashboard_data(n_jours=n_jours)
        return templates.TemplateResponse("dashboard.html", {"request": request, "data": data})
    except Exception as e:
        raise _http_500("dashboard_failed", e)


@router.get("/dashboard/data")
def dashboard_data(n_jours: int = 200) -> JSONResponse:
    try:
        return JSONResponse(DigitalTwinService().dashboard_data(n_jours=n_jours))
    except Exception as e:
        raise _http_500("dashboard_data_failed", e)


@router.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)
