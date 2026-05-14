"""HTTP routes for the FastAPI ML wrapper."""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from .config import PROXY_TARGET_WARNING
from .models.plant_expression import (
    PipelineRequest,
    PipelineResponse,
    PredictRequest,
    PredictResponse,
    SuggestionResponse,
)
from .predictor import (
    get_available_models,
    get_keyword_suggestions,
    get_latest_results,
    get_protein_detail,
    get_protein_options,
    get_decision_dashboard_data,
    get_structure_trace,
    predict,
    run_pipeline,
)


router = APIRouter()


@router.get("/health")
def health() -> Dict[str, str]:
    return {
        "status": "ok",
        "service": "plant-expression-ml",
        "message": "API is running",
    }


@router.get("/models")
def models() -> Dict[str, Any]:
    return get_available_models()


@router.get("/suggestions", response_model=SuggestionResponse)
def suggestions(q: str = Query(default="", description="Protein keyword prefix or search text.")) -> Dict[str, Any]:
    return get_keyword_suggestions(q)


@router.post("/run-pipeline", response_model=PipelineResponse)
def run_pipeline_endpoint(request: PipelineRequest) -> Dict[str, Any]:
    try:
        return run_pipeline(
            keyword=request.keyword,
            protein_limit=request.protein_limit,
            model=request.model,
            priority=request.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        return _pipeline_error_response(request, str(exc))
    except Exception as exc:
        return _pipeline_error_response(request, f"Pipeline failed: {exc}")


@router.post("/predict", response_model=PredictResponse)
def predict_endpoint(request: PredictRequest) -> Dict[str, Any]:
    return predict(request)


@router.get("/latest-results")
def latest_results() -> Dict[str, Any]:
    return get_latest_results()


@router.get("/protein-options")
def protein_options() -> Dict[str, Any]:
    return get_protein_options()


@router.get("/protein-detail")
def protein_detail(
    accession: str = Query(default="", description="Protein accession from the latest generated dataset."),
    host: str = Query(default="", description="Plant host context for host-specific DNA optimization."),
) -> Dict[str, Any]:
    return get_protein_detail(accession=accession or None, host=host or None)


@router.get("/decision-dashboard")
def decision_dashboard() -> Dict[str, Any]:
    return get_decision_dashboard_data()


@router.get("/structure-trace")
def structure_trace(
    accession: str = Query(default="", description="Protein accession from the latest generated dataset."),
    host: str = Query(default="", description="Plant host context for host-specific DNA optimization."),
    color_by_hydrophobicity: bool = Query(default=True),
    max_atoms: int = Query(default=900, ge=50, le=3000),
) -> Dict[str, Any]:
    return get_structure_trace(
        accession=accession or None,
        host=host or None,
        color_by_hydrophobicity=color_by_hydrophobicity,
        max_atoms=max_atoms,
    )


def _pipeline_error_response(request: PipelineRequest, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "keyword": request.keyword,
            "protein_limit": request.protein_limit,
            "rows_generated": 0,
            "metrics": {},
            "recommended_model": None,
            "recommended_model_reason": "",
            "priority": request.priority,
            "model_comparison": {},
            "model_lab": {},
            "artifacts": {},
            "proxy_warning": PROXY_TARGET_WARNING,
            "message": message,
        },
    )
