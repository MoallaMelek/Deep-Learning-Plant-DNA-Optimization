from __future__ import annotations

import hashlib
import re


def slugify(value: str) -> str:
    compact = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return compact[:80] or "research_topic"


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

