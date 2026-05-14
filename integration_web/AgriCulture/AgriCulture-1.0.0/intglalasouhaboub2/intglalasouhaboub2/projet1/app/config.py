from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """
    Central configuration for inference.

    Notebook-derived defaults:
    - input size: 224x224
    - normalization: rescale=1./255
    - RGB images
    """

    input_size: tuple[int, int] = (224, 224)
    num_channels: int = 3
    # L'ordre alphabétique de flow_from_directory
    labels: tuple[str, str, str] = ("disease", "healthy", "stress")

    # Expect a Keras-saved model compatible with tf.keras.models.load_model.
    # Place the file at: project_root/models/best_model.h5 (default) or update this path.
    model_path: Path = Path(__file__).resolve().parents[1] / "models" / "best_model.h5"

settings = Settings()

print("MODEL PATH:", settings.model_path)
print("FILE EXISTS:", settings.model_path.exists())