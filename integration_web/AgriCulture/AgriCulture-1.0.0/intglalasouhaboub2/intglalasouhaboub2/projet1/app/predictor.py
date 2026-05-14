from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.config import settings


@dataclass(frozen=True)
class Prediction:
    label: str
    confidence: float


class WheatPredictor:
    def __init__(self, model: Any) -> None:
        self._model = model
        self._labels = settings.labels

    def predict(self, batch: np.ndarray) -> Prediction:
        try:
            import tensorflow as tf
        except ModuleNotFoundError as e:
            raise RuntimeError("TensorFlow is not installed.") from e

        x = tf.convert_to_tensor(batch, dtype=tf.float32)
        probs = self._model(x, training=False)[0]  # softmax déjà dans le modèle

        idx = int(tf.argmax(probs).numpy())
        conf = float(tf.reduce_max(probs).numpy())
        label = self._labels[idx] if 0 <= idx < len(self._labels) else "unknown"

        return Prediction(label=label, confidence=conf)