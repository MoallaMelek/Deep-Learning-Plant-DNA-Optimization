from __future__ import annotations

from typing import List, Optional, Dict, Any
from functools import lru_cache

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, field_validator

from app.config import (
    OBJECTIVE_LABELS,
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_N_OLIGOS_PER_MUT,
    DEFAULT_TOP_N,
    DEFAULT_MAX_OFF_TARGET_RISK,
)
from app.predictor import ODMPredictor
from app.utils.preprocessing import resolve_sequence, validate_sequence, clean_sequence

router = APIRouter()

# ── Lazy singleton ──────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_predictor() -> ODMPredictor:
    """Initialise predictor once (no CRISPR data by default — XGBoost uses heuristic)."""
    return ODMPredictor(crispr_df=None, dnabert_wrapper=None)


# ──────────────────────────────────────────────────────────────────────────
# Input schema
# ──────────────────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    # ── Sequence input (one of the two options must be provided) ──────────
    sequence: Optional[str] = Field(
        default=None,
        description=(
            "Full DNA target sequence (5' → 3', ATCGN only, ≥ 50 bp). "
            "If provided, start_primer / end_primer are ignored."
        ),
        examples=["ATGGTCAAGACCTTCATCAACGAGCTGGAGCTGGAGCACATCGACAACATCCAGAGCAAGGACCTGGTC"],
    )
    start_primer: Optional[str] = Field(
        default=None,
        description="5' flanking primer (used when full sequence is unknown).",
    )
    end_primer: Optional[str] = Field(
        default=None,
        description="3' flanking primer (used when full sequence is unknown).",
    )
    estimated_length: int = Field(
        default=400,
        ge=50,
        le=10_000,
        description="Estimated full amplicon length in bp (only used with primer pair).",
    )

    # ── Agronomic objective ───────────────────────────────────────────────
    objective: str = Field(
        default="herbicide_tolerance",
        description=(
            "Agronomic objective key. "
            "Choose from: disease_resistance, yield_improvement, herbicide_tolerance, "
            "drought_tolerance, starch_quality."
        ),
        examples=["herbicide_tolerance"],
    )

    # ── Pipeline parameters ───────────────────────────────────────────────
    max_candidates: int = Field(
        default=DEFAULT_MAX_CANDIDATES, ge=1, le=100,
        description="Maximum mutation candidates to evaluate.",
    )
    n_oligos_per_mutation: int = Field(
        default=DEFAULT_N_OLIGOS_PER_MUT, ge=1, le=10,
        description="Number of ODM oligos designed per mutation.",
    )
    top_n: int = Field(
        default=DEFAULT_TOP_N, ge=1, le=50,
        description="Number of top results to return.",
    )
    max_off_target_risk: float = Field(
        default=DEFAULT_MAX_OFF_TARGET_RISK, ge=0.0, le=1.0,
        description="Maximum allowed off-target risk score (0 = strict, 1 = permissive).",
    )

    # ── Genomic localisation (optional) ──────────────────────────────────
    genomic_start: Optional[int] = Field(
        default=None,
        description="Chromosomal start position (activates GFF3 region annotation).",
    )
    genomic_chrom: str = Field(
        default="1A",
        description="Wheat chromosome identifier (e.g. 1A, 2B, 3D).",
    )

    @field_validator("objective")
    @classmethod
    def validate_objective(cls, v: str) -> str:
        valid = list(OBJECTIVE_LABELS.keys())
        if v not in valid:
            raise ValueError(f"Invalid objective '{v}'. Choose from: {valid}")
        return v

    @field_validator("sequence", "start_primer", "end_primer", mode="before")
    @classmethod
    def clean_seq_fields(cls, v):
        if v is None:
            return v
        return clean_sequence(str(v))


# ──────────────────────────────────────────────────────────────────────────
# Output schema
# ──────────────────────────────────────────────────────────────────────────

class OligoResult(BaseModel):
    rank:                      int
    oligo_sequence:            str
    oligo_length:              int
    strand:                    str
    mutation:                  str
    position:                  int
    predicted_effect:          str
    functional_region:         str
    gc_pct:                    float
    tm_celsius:                float
    delta_g:                   float
    off_target_risk:           float
    predicted_efficiency_pct:  float
    success_probability:       float
    odm_score:                 float
    mutation_score:            float
    global_score:              float


class PredictSummary(BaseModel):
    best_mutation:              Optional[str]
    best_oligo:                 Optional[str]
    best_global_score:          Optional[float]
    best_predicted_effect:      Optional[str]
    best_gc_pct:                Optional[float]
    best_tm:                    Optional[float]
    best_success_probability:   Optional[float]


class PredictResponse(BaseModel):
    status:                  str
    objective:               str
    objective_description:   str
    sequence_length:         int
    n_mutations_evaluated:   int
    n_oligos_designed:       int
    results:                 List[OligoResult]
    summary:                 PredictSummary
    message:                 Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────

@router.get("/health", tags=["system"])
def health_check() -> Dict[str, Any]:
    """
    Health check.

    Returns pipeline readiness and available objectives.
    """
    return {
        "status":     "ok",
        "pipeline":   "ODM Wheat v4",
        "objectives": OBJECTIVE_LABELS,
    }


@router.post("/predict", response_model=PredictResponse, tags=["prediction"])
def predict(body: PredictRequest) -> PredictResponse:
    """
    Run the ODM oligonucleotide design pipeline.

    ## Input
    Provide **either** a `sequence` (full DNA string) **or** a
    `start_primer` + `end_primer` pair.  All other fields are optional.

    ## Output
    Returns ranked ODM oligonucleotide candidates with physicochemical
    properties and predicted efficiency scores.

    ### Objective keys
    | Key | Description |
    |-----|-------------|
    | `disease_resistance`  | Fungal resistance (rust, powdery mildew) |
    | `yield_improvement`   | Grain weight / yield |
    | `herbicide_tolerance` | Sulfonylurea / imidazolinone tolerance |
    | `drought_tolerance`   | Water-stress tolerance |
    | `starch_quality`      | Starch composition modification |
    """
    # ── Resolve sequence ───────────────────────────────────────────────────
    try:
        resolved_seq, seq_info = resolve_sequence(
            body.sequence or "",
            body.start_primer or "",
            body.end_primer or "",
            body.estimated_length,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    ok, err = validate_sequence(resolved_seq)
    if not ok:
        raise HTTPException(status_code=422, detail=err)

    # ── Run predictor ──────────────────────────────────────────────────────
    predictor = get_predictor()
    try:
        raw = predictor.predict(
            sequence=resolved_seq,
            objective_key=body.objective,
            max_candidates=body.max_candidates,
            n_oligos_per_mut=body.n_oligos_per_mutation,
            top_n=body.top_n,
            max_off_target_risk=body.max_off_target_risk,
            genomic_start=body.genomic_start,
            genomic_chrom=body.genomic_chrom,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction error: {exc}")

    # ── Shape response ─────────────────────────────────────────────────────
    return PredictResponse(
        status=raw["status"],
        objective=body.objective,
        objective_description=OBJECTIVE_LABELS[body.objective],
        sequence_length=raw["sequence_length"],
        n_mutations_evaluated=raw["n_mutations_evaluated"],
        n_oligos_designed=raw["n_oligos_designed"],
        results=[OligoResult(**r) for r in raw["results"]],
        summary=PredictSummary(**raw["summary"]),
        message=raw.get("message"),
    )


@router.get("/objectives", tags=["metadata"])
def list_objectives() -> Dict[str, str]:
    """List all available agronomic objectives with their descriptions."""
    return OBJECTIVE_LABELS
