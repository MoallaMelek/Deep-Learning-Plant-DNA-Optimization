"""UniProt protein sequence fetcher with batching support."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse
import time
import re

import requests

from .config import UniprotConfig
from .utils import setup_logger


@dataclass(frozen=True)
class ProteinRecord:
    accession: str
    protein_name: str
    organism: str
    sequence: str


class UniprotFetcher:
    def __init__(self, config: Optional[UniprotConfig] = None) -> None:
        self.config = config or UniprotConfig()
        self.logger = setup_logger(self.__class__.__name__)
        self._session = requests.Session()

    def fetch(self, keyword: str, limit: int) -> List[ProteinRecord]:
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            self.logger.warning("Invalid UniProt limit %r; returning no records", limit)
            return []
        if limit <= 0:
            return []
        keyword = (keyword or "").strip()
        if not keyword:
            self.logger.warning("Empty UniProt keyword; returning no records")
            return []
        self.logger.info("Fetching %s proteins for keyword '%s'", limit, keyword)
        records: List[ProteinRecord] = []
        cursor = None
        remaining = limit

        while remaining > 0:
            page_size = min(self.config.batch_size, remaining)
            batch = self._fetch_page(keyword, page_size, cursor)
            if not batch["items"]:
                break
            records.extend(batch["items"])
            remaining = limit - len(records)
            cursor = batch["cursor"]
            if cursor is None:
                break

        self.logger.info("Fetched %s proteins", len(records))
        return records[:limit]

    def count(self, keyword: str) -> Optional[int]:
        keyword = (keyword or "").strip()
        if not keyword:
            self.logger.warning("Empty UniProt keyword; cannot count results")
            return None

        params = {
            "query": keyword,
            "format": "json",
            "fields": self.config.fields,
            "size": 0,
        }
        url = f"{self.config.base_url}?{urlencode(params)}"
        headers = {"User-Agent": self.config.user_agent}

        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = self._session.get(url, headers=headers, timeout=self.config.timeout_sec)
                response.raise_for_status()
                total_header = response.headers.get("x-total-results") or response.headers.get("X-Total-Results")
                if total_header:
                    try:
                        return int(total_header)
                    except ValueError:
                        self.logger.warning("UniProt count header not numeric: %r", total_header)
                        return None
                self.logger.warning("UniProt count header missing")
                return None
            except (requests.RequestException, ValueError) as exc:
                self.logger.warning("UniProt count request failed (attempt %s): %s", attempt, exc)
                if attempt < self.config.max_retries:
                    time.sleep(self._retry_delay(exc, attempt))

        self.logger.error("UniProt count request failed after %s attempts", self.config.max_retries)
        return None

    def _fetch_page(self, keyword: str, size: int, cursor: Optional[str]) -> Dict[str, Any]:
        params = {
            "query": keyword,
            "format": "json",
            "fields": self.config.fields,
            "size": size,
        }
        if cursor:
            params["cursor"] = cursor

        url = f"{self.config.base_url}?{urlencode(params)}"
        headers = {"User-Agent": self.config.user_agent}

        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = self._session.get(url, headers=headers, timeout=self.config.timeout_sec)
                response.raise_for_status()
                try:
                    data = response.json()
                except ValueError as exc:
                    raise ValueError("UniProt returned malformed JSON") from exc
                items = self._parse_items(data)
                next_cursor = self._next_cursor(response)
                return {"items": items, "cursor": next_cursor}
            except (requests.RequestException, ValueError) as exc:
                self.logger.warning("UniProt request failed (attempt %s): %s", attempt, exc)
                if attempt < self.config.max_retries:
                    time.sleep(self._retry_delay(exc, attempt))

        self.logger.error("UniProt request failed after %s attempts", self.config.max_retries)
        return {"items": [], "cursor": None}

    def _retry_delay(self, exc: Exception, attempt: int) -> float:
        response = getattr(exc, "response", None)
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return min(float(retry_after), 30.0)
                except ValueError:
                    pass
        return min(1.0 * attempt, 10.0)

    def _parse_items(self, data: Dict) -> List[ProteinRecord]:
        records: List[ProteinRecord] = []
        for entry in data.get("results", []):
            accession = entry.get("primaryAccession", "")
            protein_name = self._extract_protein_name(entry)
            organism = self._extract_organism(entry)
            sequence = entry.get("sequence", {}).get("value", "")
            if accession and sequence:
                records.append(
                    ProteinRecord(
                        accession=accession,
                        protein_name=protein_name,
                        organism=organism,
                        sequence=sequence,
                    )
                )
        return records

    def _extract_protein_name(self, entry: Dict) -> str:
        recommended = entry.get("proteinDescription", {}).get("recommendedName", {})
        full_name = recommended.get("fullName", {})
        if isinstance(full_name, dict):
            return full_name.get("value", "Unknown")
        if isinstance(full_name, str):
            return full_name
        return "Unknown"

    def _extract_organism(self, entry: Dict) -> str:
        return entry.get("organism", {}).get("scientificName", "Unknown")

    def _next_cursor(self, response: requests.Response) -> Optional[str]:
        link = response.headers.get("Link")
        if not link:
            return None
        for match in re.finditer(r'<([^>]+)>;\s*rel="([^"]+)"', link):
            next_url, rel = match.groups()
            if rel != "next":
                continue
            query_params = parse_qs(urlparse(next_url).query)
            cursor_values = query_params.get("cursor") or []
            if cursor_values and cursor_values[0]:
                return cursor_values[0]
        return None
