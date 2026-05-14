from __future__ import annotations

import logging
import os
import ssl
import urllib.request
from typing import Any

from Bio import Entrez

from app.config import settings

logger = logging.getLogger(__name__)


class NCBIService:
    def __init__(self) -> None:
        Entrez.email = settings.ncbi_email
        self.last_status: dict[str, Any] = {"available": True, "used_fallback": False, "message": ""}
        self._configure_ssl_for_entrez()

    def _configure_ssl_for_entrez(self) -> None:
        # Biopython Entrez uses urllib under the hood, so we install an opener
        # with an explicit SSL context to support enterprise/local CA chains.
        disable_verify = os.getenv("NCBI_SSL_NO_VERIFY", "").strip().lower() in {"1", "true", "yes"}
        if disable_verify:
            logger.warning("NCBI SSL verification is disabled via NCBI_SSL_NO_VERIFY.")
            context = ssl._create_unverified_context()
            urllib.request.install_opener(
                urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))
            )
            return

        cert_file = (
            os.getenv("NCBI_SSL_CERT_FILE")
            or os.getenv("SSL_CERT_FILE")
            or os.getenv("REQUESTS_CA_BUNDLE")
        )
        if not cert_file:
            try:
                import certifi

                cert_file = certifi.where()
            except Exception:
                cert_file = None

        context = ssl.create_default_context(cafile=cert_file) if cert_file else ssl.create_default_context()
        urllib.request.install_opener(
            urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))
        )

    def lookup_sequence(self, sequence: str) -> list[dict[str, Any]]:
        try:
            term = f"{sequence[:20]}[All Fields]"
            search = Entrez.esearch(db="nucleotide", term=term, retmax=3)
            search_record = Entrez.read(search)
            ids = search_record.get("IdList", [])
            if not ids:
                self.last_status = {
                    "available": True,
                    "used_fallback": False,
                    "message": "NCBI query returned no matching sequence records.",
                }
                return []
            fetched = Entrez.efetch(db="nucleotide", id=",".join(ids), rettype="gb", retmode="text")
            text = fetched.read()
            self.last_status = {
                "available": True,
                "used_fallback": False,
                "message": f"Retrieved {len(ids)} NCBI nucleotide records.",
            }
            return [{"source": "NCBI", "record_ids": ids, "raw_record": text[:3000]}]
        except Exception as exc:  # noqa: BLE001
            logger.warning("NCBI lookup failed, using fallback: %s", exc)
            self.last_status = {
                "available": False,
                "used_fallback": True,
                "message": f"NCBI unavailable: {exc}",
            }
            return [{"source": "NCBI", "record_ids": [], "raw_record": "No NCBI record found or connection unavailable."}]
