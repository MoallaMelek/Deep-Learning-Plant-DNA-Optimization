from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent


class PlannerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("PlannerAgent")

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        topic = context["topic"]
        has_dna = bool(context.get("dna_sequence"))
        tasks = [
            f"Collect background evidence for '{topic}' from NCBI/UniProt",
            f"Retrieve and summarize PubMed papers for '{topic}'",
            "Store evidence in ChromaDB and retrieve most relevant snippets",
            "Draft and critique a structured scientific article",
        ]
        if has_dna:
            tasks.insert(2, "Run DNA sequence analytics (ORFs, GC, motifs, translation, embeddings)")
        return {"tasks": tasks}

