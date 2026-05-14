from __future__ import annotations

import io
from typing import Final

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.config import settings


def load_rgb_image(image_bytes: bytes) -> np.ndarray:
    """
    Charge l'image exactement comme le notebook :
    cv2 → BGR2RGB → array numpy
    """
    arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    return img_rgb


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """
    Preprocessing identique au notebook cell 26 :
    - cv2.resize (224, 224)
    - / 255.0
    - expand_dims batch
    """
    img_resized = cv2.resize(image, (224, 224))          # INTER_LINEAR par défaut
    img_array = np.expand_dims(img_resized / 255.0, axis=0).astype(np.float32)
    return img_array