from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from app.agents.critic import CriticAgent
from app.agents.dna import DNAAgent
from app.agents.evidence import EvidenceAgent
from app.agents.literature import LiteratureAgent
from app.agents.planner import PlannerAgent
from app.agents.supervisor import SupervisorAgent
from app.agents.writer import WriterAgent
from app.config import settings
from app.services.dna_analysis import DNAAnalyzer
from app.services.embeddings import DNAEmbedder
from app.services.latex_builder import LatexBuilder
from app.services.ncbi_service import NCBIService
from app.services.pubmed_service import PubMedService
from app.services.report_exporter import ReportExporter
from app.services.uniprot_service import UniProtService
from app.services.vector_store import VectorStore
from app.utils.text import slugify, stable_hash


class ResearchPipeline:
    def __init__(self, output_root: Path | None = None) -> None:
        self.output_root = output_root or settings.output_dir
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.vector_store = VectorStore()
        self.ncbi_service = NCBIService()
        self.uniprot_service = UniProtService()
        self.pubmed_service = PubMedService()
        self.dna_analyzer = DNAAnalyzer()
        self.dna_embedder = DNAEmbedder()
        self.supervisor = SupervisorAgent(
            planner=PlannerAgent(),
            evidence=EvidenceAgent(self.ncbi_service, self.uniprot_service),
            literature=LiteratureAgent(self.pubmed_service),
            dna=DNAAgent(self.dna_analyzer, self.dna_embedder),
            writer=WriterAgent(),
            critic=CriticAgent(),
        )
        self.latex_builder = LatexBuilder()
        self.exporter = ReportExporter()

    def run(self, topic: str, dna_sequence: str | None = None, max_revision_rounds: int = 2) -> dict[str, Any]:
        run_id = f"{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}_{stable_hash(topic)}"
        run_dir = self.output_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        context = {"topic": topic, "dna_sequence": dna_sequence, "run_dir": str(run_dir)}
        result = self.supervisor.run(context, max_revision_rounds=max_revision_rounds)

        self._index_evidence(topic, result)
        retrieved = self.vector_store.query("research_evidence", topic, n_results=4)
        result["retrieved_context"] = retrieved
        result["paper"]["figure_paths"] = result.get("dna_analysis", {}).get("figure_paths", []) if result.get("dna_analysis") else []

        base_name = slugify(topic)
        tex_path = run_dir / f"{base_name}.tex"
        self.latex_builder.build_tex(result["paper"], tex_path)
        pdf_path, latex_status = self.latex_builder.compile_pdf(tex_path, run_dir, report=result["paper"])
        json_path = run_dir / f"{base_name}.json"
        fallbacks = self._collect_fallbacks(result, latex_status)
        warnings = self._collect_warnings(fallbacks)

        report_json = {
            "topic": topic,
            "generated_at": dt.datetime.now().isoformat(),
            "plan": result["plan"],
            "evidence": result["evidence"],
            "literature": result["literature"],
            "dna_analysis": result["dna_analysis"],
            "paper": result["paper"],
            "critiques": result["critiques"],
            "retrieved_context": retrieved,
            "fallbacks": fallbacks,
            "warnings": warnings,
            "outputs": {
                "pdf_path": str(pdf_path.resolve()),
                "tex_path": str(tex_path.resolve()),
                "json_path": str(json_path.resolve()),
                "figure_paths": result["paper"]["figure_paths"],
            },
        }
        self.exporter.write_json(report_json, json_path)
        return report_json["outputs"] | {
            "report": report_json,
            "fallbacks": fallbacks,
            "warnings": warnings,
        }

    def _index_evidence(self, topic: str, result: dict[str, Any]) -> None:
        docs: list[dict[str, Any]] = []
        for i, paper in enumerate(result["literature"]["papers"]):
            text = f"{paper.get('title', '')}. {paper.get('abstract', '')}"
            docs.append({"id": f"paper_{i}_{stable_hash(text)}", "text": text, "metadata": {"type": "paper", "topic": topic}})
        for i, item in enumerate(result["evidence"]):
            text = str(item)
            docs.append({"id": f"evidence_{i}_{stable_hash(text)}", "text": text, "metadata": {"type": "evidence", "topic": topic}})
        dna = result.get("dna_analysis")
        if dna:
            text = f"GC={dna['gc_percent']} ORFs={len(dna['orfs'])} motifs={list(dna['motifs'].keys())}"
            docs.append({"id": f"dna_{stable_hash(text)}", "text": text, "metadata": {"type": "dna", "topic": topic}})
        self.vector_store.add_documents("research_evidence", docs)

    def _collect_fallbacks(self, result: dict[str, Any], latex_status: dict[str, Any]) -> dict[str, dict[str, Any]]:
        status = result.get("service_status", {})
        dna_status = status.get("dna", {})
        embedding_status = dna_status.get("embedding", {}) if isinstance(dna_status, dict) else {}
        return {
            "pubmed": status.get("pubmed", {"available": True, "used_fallback": False, "message": "unknown"}),
            "ncbi": status.get("ncbi", {"available": True, "used_fallback": False, "message": "unknown"}),
            "uniprot": status.get("uniprot", {"available": True, "used_fallback": False, "message": "unknown"}),
            "pdflatex": latex_status,
            "dnabert": {
                "available": embedding_status.get("available", True),
                "used_fallback": embedding_status.get("used_fallback", False),
                "provider": embedding_status.get("provider", "unknown"),
                "message": embedding_status.get("message", "Embedding status unavailable."),
            },
        }

    def _collect_warnings(self, fallbacks: dict[str, dict[str, Any]]) -> list[str]:
        warnings: list[str] = []
        for service_name, status in fallbacks.items():
            if bool(status.get("used_fallback")):
                message = str(status.get("message", "Fallback mode activated."))
                warnings.append(f"{service_name}: {message}")
        return warnings
