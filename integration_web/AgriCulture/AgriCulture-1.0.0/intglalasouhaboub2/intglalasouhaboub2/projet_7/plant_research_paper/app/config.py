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


def _resolve_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path)


def _default_latex_engine() -> str:
    env_value = os.getenv("LATEX_ENGINE")
    if env_value:
        return env_value

    local_appdata = os.getenv("LOCALAPPDATA")
    if local_appdata:
        miktex_pdflatex = Path(local_appdata) / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64" / "pdflatex.exe"
        if miktex_pdflatex.exists():
            return str(miktex_pdflatex)

    return "pdflatex"


@dataclass(slots=True)
class Settings:
    base_dir: Path = Path(__file__).resolve().parents[1]
    app_name: str = "Plant DNA Research Assistant"
    app_version: str = "2.0.0"
    ncbi_email: str = os.getenv("NCBI_EMAIL", "your_email@example.com")
    uniprot_base_url: str = "https://rest.uniprot.org/uniprotkb/search"
    chroma_dir: Path = None  # type: ignore[assignment]
    output_dir: Path = None  # type: ignore[assignment]
    max_pubmed_results: int = int(os.getenv("MAX_PUBMED_RESULTS", "8"))
    max_uniprot_results: int = int(os.getenv("MAX_UNIPROT_RESULTS", "5"))
    latex_engine: str = _default_latex_engine()
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    demo_topic: str = os.getenv("DEMO_TOPIC", "Drought resistance genes in maize")
    demo_dna_sequence: str = os.getenv("DEMO_DNA_SEQUENCE", "ATGCGTACGTAGCTAGCTAGCTAG")
    cors_origins: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.chroma_dir = _resolve_path(os.getenv("CHROMA_DIR", "data/chroma"), self.base_dir)
        self.output_dir = _resolve_path(os.getenv("OUTPUT_DIR", "outputs"), self.base_dir)
        self.cors_origins = _parse_csv_env(
            os.getenv("CORS_ORIGINS"),
            ["http://localhost:5173", "http://localhost:3000"],
        )


settings = Settings()
