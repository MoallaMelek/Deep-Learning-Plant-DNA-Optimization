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
    app_name: str = "Plant Simulator API"
    app_version: str = "2.0.0"
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8001"))
    artifacts_dir: Path = Path(os.getenv("ARTIFACTS_DIR", "artifacts"))
    outputs_dir: Path = Path(os.getenv("OUTPUTS_DIR", "outputs"))
    media_dir: Path = Path(os.getenv("MEDIA_DIR", "media"))
    default_days: int = int(os.getenv("DEFAULT_SIMULATION_DAYS", "60"))
    auto_train_if_missing: bool = os.getenv("AUTO_TRAIN_IF_MISSING", "true").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    cors_origins: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.cors_origins = _parse_csv_env(
            os.getenv("CORS_ORIGINS"),
            ["http://localhost:5173", "http://localhost:3000"],
        )
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
