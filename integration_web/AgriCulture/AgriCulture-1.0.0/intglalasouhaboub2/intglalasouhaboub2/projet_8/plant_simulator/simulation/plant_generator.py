"""Procedural 3D mesh generation from growth predictions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pyvista as pv


@dataclass
class MeshSpec:
    mesh: pv.PolyData
    color: str
    opacity: float = 1.0


class PlantGenerator:
    """Converts a single-day prediction row into plant geometry."""

    def build_day_geometry(self, prediction_row) -> List[MeshSpec]:
        height_cm = float(prediction_row["height_cm"])
        leaf_count = int(prediction_row["leaf_count"])
        leaf_size = float(prediction_row["leaf_size_cm2"])
        stem_mm = float(prediction_row["stem_thickness_mm"])
        branch_count = int(prediction_row["branch_count"])
        health = float(prediction_row["health_index"])

        z_height = max(0.2, height_cm / 20.0)  # world units
        stem_radius = max(0.02, stem_mm / 80.0)
        leaf_radius = max(0.03, np.sqrt(leaf_size) / 16.0)

        health_green = int(np.clip(100 + 140 * health, 80, 255))
        leaf_color = f"#{40:02x}{health_green:02x}{45:02x}"
        stem_color = "#5D3A1A"

        specs: List[MeshSpec] = []

        stem = pv.Cylinder(center=(0, 0, z_height / 2), direction=(0, 0, 1), radius=stem_radius, height=z_height)
        specs.append(MeshSpec(mesh=stem, color=stem_color))

        branch_nodes = self._build_branches(
            branch_count=branch_count, z_height=z_height, stem_radius=stem_radius, leaf_radius=leaf_radius
        )
        specs.extend(branch_nodes)

        leaves = self._build_leaves(
            leaf_count=leaf_count,
            z_height=z_height,
            stem_radius=stem_radius,
            leaf_radius=leaf_radius,
            color=leaf_color,
        )
        specs.extend(leaves)
        return specs

    def _build_branches(self, branch_count: int, z_height: float, stem_radius: float, leaf_radius: float) -> List[MeshSpec]:
        if branch_count <= 0:
            return []

        specs: List[MeshSpec] = []
        for i in range(branch_count):
            angle = (2 * np.pi * i) / max(1, branch_count)
            z0 = 0.25 * z_height + (0.6 * z_height) * ((i + 1) / (branch_count + 1))
            direction = np.array([np.cos(angle), np.sin(angle), 0.45])
            direction /= np.linalg.norm(direction)
            length = 0.15 + 0.08 * z_height
            center = np.array([0.0, 0.0, z0]) + direction * (length / 2.0)
            branch = pv.Cylinder(
                center=tuple(center.tolist()),
                direction=tuple(direction.tolist()),
                radius=max(stem_radius * 0.45, 0.01),
                height=length,
            )
            specs.append(MeshSpec(mesh=branch, color="#6E4623"))

            tip = np.array([0.0, 0.0, z0]) + direction * length
            tip_leaf = pv.ParametricEllipsoid(
                xradius=leaf_radius * 0.9,
                yradius=leaf_radius * 0.5,
                zradius=leaf_radius * 0.18,
                center=tuple(tip.tolist()),
            )
            specs.append(MeshSpec(mesh=tip_leaf, color="#3f8f3f"))
        return specs

    def _build_leaves(
        self, leaf_count: int, z_height: float, stem_radius: float, leaf_radius: float, color: str
    ) -> List[MeshSpec]:
        specs: List[MeshSpec] = []
        max_leaves = int(np.clip(leaf_count, 1, 120))
        for i in range(max_leaves):
            spiral = i * 2.3999632297  # golden angle
            r = stem_radius + 0.05 + 0.006 * (i % 7)
            z = np.clip(0.1 * z_height + (i / max(1, max_leaves - 1)) * 0.88 * z_height, 0.05, z_height * 0.98)
            center = (r * np.cos(spiral), r * np.sin(spiral), z)
            leaf = pv.ParametricEllipsoid(
                xradius=leaf_radius,
                yradius=leaf_radius * 0.48,
                zradius=leaf_radius * 0.12,
                center=center,
            )
            specs.append(MeshSpec(mesh=leaf, color=color, opacity=0.97))
        return specs
