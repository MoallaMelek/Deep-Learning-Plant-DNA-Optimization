from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipeline.research_pipeline import ResearchPipeline
from app.schemas import AssetUrls, GenerateRequest, GenerateResponse, HealthResponse, ReportSummary


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
            asset_urls=self._build_asset_urls(result),
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

    def latest(self) -> GenerateResponse:
        latest_file = self._find_latest_report_file()
        if latest_file is None:
            raise ValueError("No generated research reports were found in outputs/.")

        report_payload = json.loads(latest_file.read_text(encoding="utf-8"))
        outputs = report_payload.get("outputs") or {}
        summary_payload = self._build_summary(report_payload)
        return GenerateResponse(
            pdf_path=outputs.get("pdf_path", ""),
            tex_path=outputs.get("tex_path", ""),
            json_path=outputs.get("json_path", str(latest_file.resolve())),
            figure_paths=outputs.get("figure_paths", report_payload.get("paper", {}).get("figure_paths", [])),
            asset_urls=self._build_asset_urls(outputs),
            summary=ReportSummary(**summary_payload),
            fallbacks=report_payload.get("fallbacks", {}),
            warnings=report_payload.get("warnings", []),
            report=report_payload,
        )

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

    def _find_latest_report_file(self) -> Path | None:
        self.pipeline.output_root.mkdir(parents=True, exist_ok=True)
        candidates = sorted(self.pipeline.output_root.glob("*/*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        return candidates[0] if candidates else None

    def _build_asset_urls(self, payload: dict[str, Any]) -> AssetUrls:
        return AssetUrls(
            pdf=self._asset_url(payload.get("pdf_path")),
            tex=self._asset_url(payload.get("tex_path")),
            json_url=self._asset_url(payload.get("json_path")),
            figures=[
                url
                for url in (self._asset_url(path_value) for path_value in payload.get("figure_paths", []))
                if url
            ],
        )

    def _asset_url(self, path_value: Any) -> str | None:
        if not path_value:
            return None

        output_root = settings.output_dir.resolve()
        raw_path = Path(str(path_value).replace("\\", "/"))

        if raw_path.is_absolute():
            try:
                relative = raw_path.resolve().relative_to(output_root)
            except ValueError:
                parts = raw_path.parts
                if "outputs" not in parts:
                    return None
                relative = Path(*parts[parts.index("outputs") + 1 :])
        else:
            parts = raw_path.parts
            relative = Path(*parts[1:]) if parts and parts[0] == settings.output_dir.name else raw_path

        relative_url = "/".join(part for part in relative.parts if part not in {"", "."})
        return f"/writing/assets/{relative_url}" if relative_url else None
