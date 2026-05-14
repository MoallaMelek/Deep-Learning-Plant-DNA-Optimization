from __future__ import annotations

from typing import Any

from app.agents.critic import CriticAgent
from app.agents.dna import DNAAgent
from app.agents.evidence import EvidenceAgent
from app.agents.literature import LiteratureAgent
from app.agents.planner import PlannerAgent
from app.agents.writer import WriterAgent


class SupervisorAgent:
    def __init__(
        self,
        planner: PlannerAgent,
        evidence: EvidenceAgent,
        literature: LiteratureAgent,
        dna: DNAAgent,
        writer: WriterAgent,
        critic: CriticAgent,
    ) -> None:
        self.planner = planner
        self.evidence = evidence
        self.literature = literature
        self.dna = dna
        self.writer = writer
        self.critic = critic

    def run(self, context: dict[str, Any], max_revision_rounds: int = 2) -> dict[str, Any]:
        plan = self.planner.run(context)
        evidence = self.evidence.run(context)
        literature = self.literature.run(context)
        dna = self.dna.run(context)

        enriched = {
            **context,
            "plan": plan["tasks"],
            "evidence": evidence["evidence"],
            "literature": literature,
            "dna_analysis": dna["dna_analysis"],
            "service_status": {
                "pubmed": literature.get("source_status", {}),
                "ncbi": evidence.get("source_status", {}).get("ncbi", {}),
                "uniprot": evidence.get("source_status", {}).get("uniprot", {}),
                "dna": dna.get("dna_status", {}),
            },
        }
        paper = self.writer.run(enriched)["paper"]

        critiques: list[dict[str, Any]] = []
        for _ in range(max_revision_rounds):
            critique = self.critic.run({"paper": paper})
            critiques.append({"issues": critique["issues"]})
            paper = critique["revised_paper"]
            if not critique["issues"]:
                break

        return {
            "plan": plan["tasks"],
            "evidence": evidence["evidence"],
            "literature": literature,
            "dna_analysis": dna["dna_analysis"],
            "paper": paper,
            "critiques": critiques,
            "service_status": enriched.get("service_status", {}),
        }
