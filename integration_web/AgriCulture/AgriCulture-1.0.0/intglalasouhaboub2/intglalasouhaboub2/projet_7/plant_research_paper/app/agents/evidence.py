from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.services.ncbi_service import NCBIService
from app.services.uniprot_service import UniProtService


class EvidenceAgent(BaseAgent):
    def __init__(self, ncbi: NCBIService, uniprot: UniProtService) -> None:
        super().__init__("EvidenceAgent")
        self.ncbi = ncbi
        self.uniprot = uniprot

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        dna_sequence = context.get("dna_sequence")
        evidence: list[dict[str, Any]] = []
        if not dna_sequence:
            return {
                "evidence": evidence,
                "source_status": {
                    "ncbi": {"available": True, "used_fallback": False, "message": "Skipped: no DNA sequence provided."},
                    "uniprot": {
                        "available": True,
                        "used_fallback": False,
                        "message": "Skipped: no DNA sequence provided.",
                    },
                },
            }

        if dna_sequence:
            evidence.extend(self.ncbi.lookup_sequence(dna_sequence))
            evidence.extend(self.uniprot.lookup_sequence(dna_sequence))
        return {
            "evidence": evidence,
            "source_status": {
                "ncbi": self.ncbi.last_status,
                "uniprot": self.uniprot.last_status,
            },
        }
