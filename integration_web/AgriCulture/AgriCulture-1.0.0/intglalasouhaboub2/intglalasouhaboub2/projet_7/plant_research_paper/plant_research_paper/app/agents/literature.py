from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.services.pubmed_service import PubMedService


class LiteratureAgent(BaseAgent):
    def __init__(self, pubmed: PubMedService) -> None:
        super().__init__("LiteratureAgent")
        self.pubmed = pubmed

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        papers = self.pubmed.search_topic(context["topic"])
        insights = []
        for paper in papers:
            sentence = f"{paper.get('title', 'Untitled')} ({paper.get('year', 'N/A')})"
            if paper.get("abstract"):
                sentence += f": {paper['abstract'][:220]}..."
            insights.append(sentence)
        return {"papers": papers, "insights": insights, "source_status": self.pubmed.last_status}
