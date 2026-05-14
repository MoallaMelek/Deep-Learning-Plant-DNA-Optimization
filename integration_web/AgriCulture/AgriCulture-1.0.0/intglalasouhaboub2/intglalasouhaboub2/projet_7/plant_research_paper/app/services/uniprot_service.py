from __future__ import annotations

import logging
from typing import Any

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class UniProtService:
    def __init__(self) -> None:
        self.last_status: dict[str, Any] = {"available": True, "used_fallback": False, "message": ""}

    def lookup_sequence(self, sequence: str) -> list[dict[str, Any]]:
        params = {
            "query": sequence[:18],
            "format": "json",
            "size": settings.max_uniprot_results,
            "fields": "accession,id,protein_name,organism_name,gene_names,length",
        }
        try:
            response = requests.get(settings.uniprot_base_url, params=params, timeout=20)
            response.raise_for_status()
            payload = response.json()
            results: list[dict[str, Any]] = []
            for row in payload.get("results", []):
                results.append(
                    {
                        "source": "UniProt",
                        "accession": row.get("primaryAccession"),
                        "id": row.get("uniProtkbId"),
                        "organism": row.get("organism", {}).get("scientificName"),
                        "protein": row.get("proteinDescription", {})
                        .get("recommendedName", {})
                        .get("fullName", {})
                        .get("value", "Unknown"),
                    }
                )
            self.last_status = {
                "available": True,
                "used_fallback": False,
                "message": f"Retrieved {len(results)} UniProt records.",
            }
            return results
        except Exception as exc:  # noqa: BLE001
            logger.warning("UniProt lookup failed, using fallback: %s", exc)
            self.last_status = {
                "available": False,
                "used_fallback": True,
                "message": f"UniProt unavailable: {exc}",
            }
            return [{"source": "UniProt", "note": "No UniProt entries returned or connection unavailable."}]
