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


@dataclass(slots=True)
class Settings:
    base_dir: Path = Path(__file__).resolve().parents[1]
    app_name: str = "Plant Simulator API"
    app_version: str = "2.0.0"
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8001"))
    artifacts_dir: Path = None  # type: ignore[assignment]
    outputs_dir: Path = None  # type: ignore[assignment]
    media_dir: Path = None  # type: ignore[assignment]
    default_days: int = int(os.getenv("DEFAULT_SIMULATION_DAYS", "60"))
    auto_train_if_missing: bool = os.getenv("AUTO_TRAIN_IF_MISSING", "true").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    cors_origins: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.artifacts_dir = _resolve_path(os.getenv("ARTIFACTS_DIR", "artifacts"), self.base_dir)
        self.outputs_dir = _resolve_path(os.getenv("OUTPUTS_DIR", "outputs"), self.base_dir)
        self.media_dir = _resolve_path(os.getenv("MEDIA_DIR", "media"), self.base_dir)
        self.cors_origins = _parse_csv_env(
            os.getenv("CORS_ORIGINS"),
            ["http://localhost:5173", "http://localhost:3000"],
        )
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
