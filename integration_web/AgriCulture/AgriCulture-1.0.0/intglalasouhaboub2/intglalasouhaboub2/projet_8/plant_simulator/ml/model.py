"""PyTorch model and artifact utilities for plant growth prediction."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import torch
import torch.nn as nn


class PlantGrowthNet(nn.Module):
    def __init__(self, input_dim: int, output_dim: int = 7):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def get_cpu_device() -> torch.device:
    return torch.device("cpu")


def save_model(model: nn.Module, path: Path, metadata: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "metadata": metadata}, path)


def load_model(path: Path) -> Tuple[PlantGrowthNet, Dict]:
    payload = torch.load(path, map_location="cpu")
    metadata = payload["metadata"]
    model = PlantGrowthNet(
        input_dim=metadata["input_dim"],
        output_dim=metadata["output_dim"],
    )
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return model, metadata
