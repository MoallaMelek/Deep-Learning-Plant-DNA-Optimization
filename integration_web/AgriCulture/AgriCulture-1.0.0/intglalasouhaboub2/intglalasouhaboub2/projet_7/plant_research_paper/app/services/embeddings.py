from __future__ import annotations

import logging
import os
from hashlib import md5
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def _default_dnabert_model() -> str:
    env_value = os.getenv("DNABERT_MODEL")
    if env_value:
        return env_value

    local_model = Path(__file__).resolve().parents[2] / "models" / "dnabert-2-117m"
    if local_model.exists():
        return str(local_model)

    return "zhihan1996/DNABERT-2-117M"


class DNAEmbedder:
    def __init__(self, model_name: str | None = None) -> None:
        if model_name is None:
            model_name = _default_dnabert_model()
        self.model_name = model_name
        self._model = None
        self._tokenizer = None
        self.last_status: dict[str, str | bool] = {
            "available": True,
            "used_fallback": False,
            "provider": model_name,
            "message": "",
        }

    def embed_sequence(self, sequence: str) -> list[float]:
        vector, _ = self.embed_with_metadata(sequence)
        return vector

    def embed_with_metadata(self, sequence: str) -> tuple[list[float], dict[str, str | bool]]:
        try:
            self._lazy_load()
            if self._model is None or self._tokenizer is None:
                self.last_status = {
                    "available": False,
                    "used_fallback": True,
                    "provider": "hash_embedding",
                    "message": "DNABERT model not loaded. Using deterministic fallback embedding.",
                }
                return self._fallback_embedding(sequence), self.last_status
            inputs = self._tokenizer(sequence, return_tensors="pt", truncation=True, max_length=512)
            outputs = self._model(**inputs)
            hidden_state = outputs.last_hidden_state if hasattr(outputs, "last_hidden_state") else outputs[0]
            vector = hidden_state.mean(dim=1).detach().cpu().numpy().flatten()
            self.last_status = {
                "available": True,
                "used_fallback": False,
                "provider": self.model_name,
                "message": "DNABERT embedding generated successfully.",
            }
            return vector.astype(float).tolist(), self.last_status
        except Exception as exc:  # noqa: BLE001
            logger.warning("DNABERT unavailable, fallback embedding used: %s", exc)
            self.last_status = {
                "available": False,
                "used_fallback": True,
                "provider": "hash_embedding",
                "message": f"DNABERT unavailable: {exc}",
            }
            return self._fallback_embedding(sequence), self.last_status

    def _lazy_load(self) -> None:
        if self._model is not None and self._tokenizer is not None:
            return
        try:
            from transformers import AutoModel, AutoTokenizer

            local_files_only = Path(self.model_name).exists()
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                local_files_only=local_files_only,
            )
            self._model = AutoModel.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                local_files_only=local_files_only,
            )
            self._model.eval()
        except Exception:  # noqa: BLE001
            self._model = None
            self._tokenizer = None

    def _fallback_embedding(self, text: str, size: int = 128) -> list[float]:
        vector = np.zeros(size, dtype=float)
        for i in range(max(1, len(text) - 2)):
            kmer = text[i : i + 3]
            idx = int(md5(kmer.encode("utf-8")).hexdigest(), 16) % size
            vector[idx] += 1.0
        norm = np.linalg.norm(vector) or 1.0
        return (vector / norm).tolist()


class TextEmbedder:
    def embed(self, text: str, size: int = 128) -> list[float]:
        vector = np.zeros(size, dtype=float)
        for token in text.lower().split():
            idx = int(md5(token.encode("utf-8")).hexdigest(), 16) % size
            vector[idx] += 1.0
        norm = np.linalg.norm(vector) or 1.0
        return (vector / norm).tolist()
