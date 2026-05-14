from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProfilePredictRequest(BaseModel):
    drought: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    salt: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    yield_: Optional[float] = Field(default=None, ge=0.0, le=1.0, alias="yield")
    disease: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    top_n: int = Field(default=5, ge=1, le=20)
    objective: str = Field(default="balanced")
    model_config = ConfigDict(populate_by_name=True)


class CrossingPredictRequest(BaseModel):
    variety_name_a: Optional[str] = None
    variety_name_b: Optional[str] = None
    snps_a: Optional[Dict[str, float]] = None
    snps_b: Optional[Dict[str, float]] = None
    model: str = "rf"
    n_simulations: int = Field(default=1, ge=1, le=100)
    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def check_at_least_one(self):
        has_names = bool(self.variety_name_a and self.variety_name_b)
        has_snps = bool(self.snps_a and self.snps_b)
        if not has_names and not has_snps:
            raise ValueError("Fournir soit (variety_name_a + variety_name_b) soit (snps_a + snps_b)")
        return self


class MonteCarloRequest(BaseModel):
    crossing_name: Optional[str] = None
    variety_name_a: Optional[str] = None
    variety_name_b: Optional[str] = None
    snps_a: Optional[Dict[str, float]] = None
    snps_b: Optional[Dict[str, float]] = None
    n_simulations: int = Field(default=1000, ge=10, le=10000)
    model: str = Field(default="rf")
    seed: int = Field(default=42)
    model_config = ConfigDict(populate_by_name=True)


class ExplainCrossingRequest(CrossingPredictRequest):
    method: str = Field(default="shap", pattern="^(shap|lime|permutation)$")
    top_n: int = Field(default=15, ge=1, le=159)


class FastaGenerateRequest(BaseModel):
    crossing_name: Optional[str] = None
    snp_names: Optional[List[str]] = None
    traits: Optional[List[str]] = None
