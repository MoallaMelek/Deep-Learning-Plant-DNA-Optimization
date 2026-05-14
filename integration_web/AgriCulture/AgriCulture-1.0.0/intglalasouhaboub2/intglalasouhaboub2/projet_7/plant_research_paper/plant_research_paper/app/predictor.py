from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipeline.research_pipeline import ResearchPipeline
from app.schemas import GenerateRequest, GenerateResponse, HealthResponse, ReportSummary


class ResearchPredictor:
    def __init__(self, pipeline: ResearchPipeline | None = None) -> None:
        self.pipeline = pipeline or ResearchPipeline()

    def health(self) -> HealthResponse:
        output_dir = settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        chroma_dir = settings.chroma_dir
        chroma_dir.mkdir(parents=True, exist_ok=True)

        latex_available = shutil.which(settings.latex_engine) is not None
        status = "ok" if latex_available else "degraded"
        return HealthResponse(
            status=status,
            version=settings.app_version,
            output_dir=str(output_dir.resolve()),
            chroma_dir=str(chroma_dir.resolve()),
            services={
                "latex": {
                    "engine": settings.latex_engine,
                    "available": latex_available,
                    "mode": "live" if latex_available else "fallback_pdf",
                },
                "pubmed": {"available": True, "mode": "live_or_fallback"},
                "ncbi": {"available": True, "mode": "live_or_fallback"},
                "uniprot": {"available": True, "mode": "live_or_fallback"},
                "dnabert": {"available": True, "mode": "live_or_fallback"},
            },
        )

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        result = self.pipeline.run(
            topic=request.topic,
            dna_sequence=request.dna_sequence,
            max_revision_rounds=request.max_revision_rounds,
        )
        summary_payload = self._build_summary(result["report"])
        return GenerateResponse(
            pdf_path=result["pdf_path"],
            tex_path=result["tex_path"],
            json_path=result["json_path"],
            figure_paths=result.get("figure_paths", []),
            summary=ReportSummary(**summary_payload),
            fallbacks=result.get("fallbacks", {}),
            warnings=result.get("warnings", []),
            report=result["report"],
        )

    def generate_demo(self) -> GenerateResponse:
        demo_request = GenerateRequest(
            topic=settings.demo_topic,
            dna_sequence=settings.demo_dna_sequence,
            max_revision_rounds=1,
        )
        return self.generate(demo_request)

    def _build_summary(self, report: dict[str, Any]) -> dict[str, Any]:
        dna = report.get("dna_analysis") or {}
        paper = report.get("paper") or {}
        literature = report.get("literature") or {}
        evidence = report.get("evidence") or []
        return {
            "topic": report.get("topic", ""),
            "title": paper.get("title", "Untitled"),
            "generated_at": report.get("generated_at", ""),
            "literature_count": len(literature.get("papers", [])),
            "evidence_count": len(evidence),
            "references_count": len(paper.get("references", [])),
            "dna_provided": bool(report.get("dna_analysis")),
            "dna_metrics": {
                "sequence_length": dna.get("sequence_length"),
                "gc_percent": dna.get("gc_percent"),
                "orf_count": len(dna.get("orfs", [])),
                "motif_count": len(dna.get("motifs", {})),
                "embedding_dim": dna.get("embedding_dim"),
            },
            "key_findings": [
                f"Literature records analyzed: {len(literature.get('papers', []))}",
                f"External evidence entries: {len(evidence)}",
                f"DNA ORFs detected: {len(dna.get('orfs', [])) if dna else 0}",
                f"GC content: {dna.get('gc_percent', 'N/A')}",
            ],
            "section_previews": {
                "abstract": (paper.get("abstract", "") or "")[:280],
                "introduction": (paper.get("introduction", "") or "")[:280],
                "methods": (paper.get("methods", "") or "")[:280],
                "results": (paper.get("results", "") or "")[:280],
                "discussion": (paper.get("discussion", "") or "")[:280],
                "conclusion": (paper.get("conclusion", "") or "")[:280],
            },
        }
