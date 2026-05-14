"""Lightweight request normalization helpers for the FastAPI wrapper.

Scientific preprocessing remains in dataset_builder/ and src/.
"""

from typing import Any, Optional


def normalize_keyword(value: Any, default: str) -> str:
    keyword = str(value or default).strip()
    return keyword or default


def normalize_model_name(value: Any) -> Optional[str]:
    if value is None:
        return None
    model = str(value).strip().lower()
    return model or None


def normalize_priority_name(value: Any, default: str = "balanced") -> str:
    priority = str(value or default).strip().lower()
    return priority if priority in {"accuracy", "speed", "interpretability", "balanced"} else default
