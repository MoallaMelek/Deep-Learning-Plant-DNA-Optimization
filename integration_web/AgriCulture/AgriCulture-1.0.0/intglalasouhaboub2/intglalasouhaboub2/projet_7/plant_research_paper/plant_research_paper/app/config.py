from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _parse_csv_env(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default
    parsed = [item.strip() for item in value.split(",") if item.strip()]
    return parsed or default


@dataclass(slots=True)
class Settings:
    app_name: str = "Plant DNA Research Assistant"
    app_version: str = "2.0.0"
    ncbi_email: str = os.getenv("NCBI_EMAIL", "your_email@example.com")
    uniprot_base_url: str = "https://rest.uniprot.org/uniprotkb/search"
    chroma_dir: Path = Path(os.getenv("CHROMA_DIR", "data/chroma"))
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "outputs"))
    max_pubmed_results: int = int(os.getenv("MAX_PUBMED_RESULTS", "8"))
    max_uniprot_results: int = int(os.getenv("MAX_UNIPROT_RESULTS", "5"))
    latex_engine: str = os.getenv("LATEX_ENGINE", "pdflatex")
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    demo_topic: str = os.getenv("DEMO_TOPIC", "Drought resistance genes in maize")
    demo_dna_sequence: str = os.getenv("DEMO_DNA_SEQUENCE", "ATGCGTACGTAGCTAGCTAGCTAG")
    cors_origins: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.cors_origins = _parse_csv_env(
            os.getenv("CORS_ORIGINS"),
            ["http://localhost:5173", "http://localhost:3000"],
        )


settings = Settings()
