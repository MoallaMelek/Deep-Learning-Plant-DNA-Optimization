"""
routes.py — Tous les endpoints de l'API G×E Blé Dur
"""
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from typing import Dict, Optional
import base64

from app.config import TRAITS
from app.utils.preprocessing import extract_all_parents

router = APIRouter()


# ── Schémas Pydantic ─────────────────────────────────────────────────────

class CrossingInput(BaseModel):
    pred_drought: float = Field(..., ge=0.0, le=1.0, description="Score sécheresse [0-1]")
    pred_salt:    float = Field(..., ge=0.0, le=1.0, description="Score salinité [0-1]")
    pred_yield:   float = Field(..., ge=0.0, le=1.0, description="Score rendement [0-1]")
    pred_disease: float = Field(..., ge=0.0, le=1.0, description="Score résistance maladies [0-1]")
    croisement:   Optional[str] = Field("Custom", description="Nom du croisement (optionnel)")

    class Config:
        json_schema_extra = {
            "example": {
                "pred_drought": 0.72, "pred_salt": 0.65,
                "pred_yield":   0.80, "pred_disease": 0.70,
                "croisement":   "KARIM x SIMETO",
            }
        }


class RecommendationRequest(BaseModel):
    variete_cible: str = Field(..., description="Nom de la variété parentale")
    poids: Dict[str, float] = Field(
        default={"yield": 0.40, "drought": 0.35, "salt": 0.15, "disease": 0.10},
        description="Poids agronomiques par trait (somme = 1.0)",
    )
    top_n: int = Field(default=5, ge=1, le=20)

    class Config:
        json_schema_extra = {
            "example": {
                "variete_cible": "KARIM",
                "poids": {"yield": 0.40, "drought": 0.35, "salt": 0.15, "disease": 0.10},
                "top_n": 5,
            }
        }


# ── Health ────────────────────────────────────────────────────────────────

@router.get("/health", tags=["Système"])
def health_check(request: Request):
    predictor = request.app.state.predictor
    return {
        "status":       "ok",
        "modele":       predictor.best_model_name,
        "croisements":  len(predictor.crossings_df),
        "predictions":  len(predictor.predictions_by_crossing),
    }


# ── Dataset ───────────────────────────────────────────────────────────────

@router.get("/croisements", tags=["Dataset"])
def liste_croisements(
    request: Request,
    limit: int = Query(50, ge=1, le=720),
    offset: int = Query(0, ge=0),
):
    """Liste paginée des croisements disponibles dans le dataset."""
    df = request.app.state.predictor.crossings_df
    total = len(df)
    subset = df["Croisement"].iloc[offset: offset + limit].tolist()
    return {"total": total, "offset": offset, "limit": limit, "croisements": subset}


@router.get("/varietes", tags=["Dataset"])
def liste_varietes(request: Request):
    """Liste toutes les variétés parentales disponibles dans le dataset."""
    df = request.app.state.predictor.crossings_df
    parents = extract_all_parents(df)
    return {"total": len(parents), "varietes": parents}


@router.get("/stats", tags=["Dataset"])
def stats_globales(request: Request):
    """Statistiques globales du dataset."""
    df = request.app.state.predictor.crossings_df
    return {
        "nb_croisements": len(df),
        "rendement_moyen_kg_ha":  round(float(df["yield_kg_ha"].mean()), 0),
        "rendement_median_kg_ha": round(float(df["yield_kg_ha"].median()), 0),
        "rendement_max_kg_ha":    round(float(df["yield_kg_ha"].max()), 0),
        "rendement_min_kg_ha":    round(float(df["yield_kg_ha"].min()), 0),
        "traits_moyens": {
            t: round(float(df[f"pred_{t}"].mean()), 4) for t in TRAITS
        },
    }


# ── Prédiction ────────────────────────────────────────────────────────────

@router.post("/predict", tags=["Prédiction"])
def predict_trajectoire(data: CrossingInput, request: Request):
    """
    Prédit la trajectoire phénologique G×E (T0→T7) pour un croisement
    défini par ses 4 traits agronomiques.

    Retourne les scores prédits pour les stades T6 et T7 + rendement estimé (kg/ha).
    """
    predictor = request.app.state.predictor
    result = predictor.predict_custom(
        pred_drought=data.pred_drought,
        pred_salt=data.pred_salt,
        pred_yield=data.pred_yield,
        pred_disease=data.pred_disease,
        croisement_name=data.croisement,
    )
    return result


@router.post("/recommend", tags=["Recommandation"])
def recommander(req: RecommendationRequest, request: Request):
    """
    Retourne les top_n croisements recommandés pour une variété parentale donnée,
    selon les poids agronomiques fournis.
    """
    # Validation des poids
    total_poids = sum(req.poids.values())
    if abs(total_poids - 1.0) > 0.01:
        raise HTTPException(
            status_code=422,
            detail=f"La somme des poids doit être 1.0 (actuelle : {total_poids:.2f})",
        )
    predictor = request.app.state.predictor
    result = predictor.recommend(
        variete_cible=req.variete_cible,
        poids=req.poids,
        top_n=req.top_n,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ── Graphiques ────────────────────────────────────────────────────────────

def _image_response(b64: Optional[str], label: str) -> HTMLResponse:
    if b64 is None:
        raise HTTPException(status_code=404, detail=f"{label} introuvable")
    html = f"""
    <!DOCTYPE html><html><body style="background:#111;margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;">
    <img src="data:image/png;base64,{b64}" style="max-width:98%;border-radius:8px;box-shadow:0 4px 24px #0008;">
    </body></html>
    """
    return HTMLResponse(content=html)


@router.get("/charts/top5", tags=["Graphiques"])
def chart_top5(request: Request):
    """Affiche les traits à maturité (T7) des 5 meilleurs croisements."""
    b64 = request.app.state.predictor.plot_top5_maturite()
    return _image_response(b64, "Top 5 maturité")


@router.get("/charts/distribution", tags=["Graphiques"])
def chart_distribution(request: Request):
    """Histogramme de distribution des rendements estimés (kg/ha)."""
    b64 = request.app.state.predictor.plot_distribution_rendement()
    return _image_response(b64, "Distribution")


@router.get("/charts/top10", tags=["Graphiques"])
def chart_top10(request: Request):
    """Top 10 croisements par rendement calibré (kg/ha)."""
    b64 = request.app.state.predictor.plot_top10_rendement()
    return _image_response(b64, "Top 10")


@router.get("/charts/trajectoire", tags=["Graphiques"])
def chart_trajectoire(
    request: Request,
    croisement: str = Query(..., description="Nom exact du croisement"),
):
    """
    Graphique 2×2 de la trajectoire G×E (T0→T7) pour un croisement existant.
    """
    b64 = request.app.state.predictor.plot_trajectoire(croisement)
    return _image_response(b64, "Trajectoire")


@router.get("/charts/variete", tags=["Graphiques"])
def chart_variete(
    request: Request,
    variete: str = Query(..., description="Nom de la variété parentale"),
    trait: str = Query("yield", description="Trait à visualiser : drought, salt, yield, disease"),
):
    """
    Série temporelle G×E — Top 5 croisements d'une variété pour un trait donné.
    """
    if trait not in TRAITS:
        raise HTTPException(status_code=422, detail=f"Trait invalide. Choisir parmi : {TRAITS}")
    poids_default = {"yield": 0.40, "drought": 0.35, "salt": 0.15, "disease": 0.10}
    b64 = request.app.state.predictor.plot_synthese_variete(variete, poids_default, trait)
    return _image_response(b64, "Synthèse variété")
