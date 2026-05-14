from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent


class CriticAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("CriticAgent")

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        paper = context["paper"]
        issues: list[str] = []

        required = ["abstract", "introduction", "methods", "results", "discussion", "conclusion"]
        additions: dict[str, str] = {
            "abstract": " This abstract should explicitly report data sources, analytical scope, and output artifacts to strengthen scientific readability.",
            "introduction": " The introduction should further clarify biological relevance and expected contribution to plant genomics workflows.",
            "methods": " Methods should make module boundaries and reproducibility assumptions explicit for downstream replication.",
            "results": " Results should include quantitative retrieval and analysis indicators to support interpretation quality.",
            "discussion": " Discussion should compare strengths, limitations, and practical constraints for real research deployment.",
            "conclusion": " The conclusion should emphasize applicability boundaries and recommended validation steps.",
        }
        for section in required:
            if len(paper.get(section, "").split()) < 35:
                issues.append(f"{section.title()} is too short and should provide more scientific detail.")

        if not paper.get("references", []):
            issues.append("References are missing.")

        revised = paper.copy()
        for section in required:
            if any(msg.lower().startswith(section) for msg in issues):
                addition = additions[section]
                if addition.strip() not in revised.get(section, ""):
                    revised[section] = revised.get(section, "") + addition

        return {"issues": issues, "revised_paper": revised}
