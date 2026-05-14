from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=6, description="Plant genetics research topic")
    dna_sequence: str | None = Field(default=None, description="Optional DNA sequence")
    max_revision_rounds: int = Field(default=2, ge=1, le=4)


class HealthResponse(BaseModel):
    status: str
    version: str
    output_dir: str
    chroma_dir: str
    services: dict[str, dict[str, Any]]


class ReportSummary(BaseModel):
    topic: str
    title: str
    generated_at: str
    literature_count: int
    evidence_count: int
    references_count: int
    dna_provided: bool
    dna_metrics: dict[str, Any]
    key_findings: list[str]
    section_previews: dict[str, str]


class AssetUrls(BaseModel):
    pdf: str | None = None
    tex: str | None = None
    json_url: str | None = None
    figures: list[str] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    pdf_path: str
    tex_path: str
    json_path: str
    figure_paths: list[str]
    asset_urls: AssetUrls | None = None
    summary: ReportSummary
    fallbacks: dict[str, dict[str, Any]]
    warnings: list[str] = Field(default_factory=list)
    report: dict[str, Any]
