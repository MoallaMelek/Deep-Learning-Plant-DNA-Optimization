from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agents.base import BaseAgent
from app.services.dna_analysis import DNAAnalyzer
from app.services.embeddings import DNAEmbedder


class DNAAgent(BaseAgent):
    def __init__(self, analyzer: DNAAnalyzer, embedder: DNAEmbedder) -> None:
        super().__init__("DNAAgent")
        self.analyzer = analyzer
        self.embedder = embedder

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        sequence = context.get("dna_sequence")
        if not sequence:
            return {
                "dna_analysis": None,
                "dna_status": {
                    "available": True,
                    "used_fallback": False,
                    "message": "Skipped: no DNA sequence provided.",
                    "embedding": {"provider": "not_applicable", "used_fallback": False},
                },
            }
        figure_dir = Path(context["run_dir"])
        try:
            result = self.analyzer.analyze(sequence, figure_dir)
            embedding, embedding_status = self.embedder.embed_with_metadata(result.normalized_sequence)
            return {
                "dna_analysis": {
                    "sequence_length": len(result.normalized_sequence),
                    "gc_percent": result.gc_percent,
                    "orfs": result.orfs,
                    "motifs": result.motifs,
                    "protein_translation": result.protein_translation,
                    "embedding_dim": len(embedding),
                    "figure_paths": result.figure_paths,
                },
                "dna_status": {
                    "available": True,
                    "used_fallback": bool(embedding_status.get("used_fallback")),
                    "message": "DNA analysis completed.",
                    "embedding": embedding_status,
                },
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "dna_analysis": None,
                "dna_status": {
                    "available": False,
                    "used_fallback": True,
                    "message": f"DNA analysis failed: {exc}",
                    "embedding": {"provider": "unavailable", "used_fallback": True},
                },
            }
