from __future__ import annotations

import logging
import re
from typing import Any

from Bio import Entrez, Medline

from app.config import settings

logger = logging.getLogger(__name__)


class PubMedService:
    def __init__(self) -> None:
        Entrez.email = settings.ncbi_email
        self.last_status: dict[str, Any] = {"available": True, "used_fallback": False, "message": ""}

    def search_topic(self, topic: str) -> list[dict[str, Any]]:
        try:
            handle = Entrez.esearch(db="pubmed", term=topic, retmax=settings.max_pubmed_results, sort="relevance")
            record = Entrez.read(handle)
            pmids = record.get("IdList", [])
            if not pmids:
                self.last_status = {
                    "available": True,
                    "used_fallback": False,
                    "message": "No PubMed records matched the query.",
                }
                return []
            fetch = Entrez.efetch(db="pubmed", id=",".join(pmids), rettype="medline", retmode="text")
            entries = Medline.parse(fetch)
            papers: list[dict[str, Any]] = []
            for item in entries:
                dp_value = item.get("DP", "")
                year_match = re.search(r"\b(19|20)\d{2}\b", dp_value)
                papers.append(
                    {
                        "pmid": item.get("PMID", ""),
                        "title": item.get("TI", ""),
                        "abstract": item.get("AB", ""),
                        "keywords": item.get("OT", []),
                        "journal": item.get("JT", ""),
                        "year": year_match.group(0) if year_match else dp_value,
                        "authors": item.get("AU", []),
                    }
                )
            self.last_status = {
                "available": True,
                "used_fallback": False,
                "message": f"Retrieved {len(papers)} PubMed records.",
            }
            return papers
        except Exception as exc:  # noqa: BLE001
            logger.warning("PubMed search failed, using fallback: %s", exc)
            self.last_status = {
                "available": False,
                "used_fallback": True,
                "message": f"PubMed unavailable: {exc}",
            }
            return [
                {
                    "pmid": "N/A",
                    "title": f"Fallback literature note for: {topic}",
                    "abstract": "Live PubMed retrieval unavailable. This placeholder keeps the pipeline reproducible locally.",
                    "keywords": ["fallback", "offline"],
                    "journal": "N/A",
                    "year": "N/A",
                    "authors": [],
                }
            ]
