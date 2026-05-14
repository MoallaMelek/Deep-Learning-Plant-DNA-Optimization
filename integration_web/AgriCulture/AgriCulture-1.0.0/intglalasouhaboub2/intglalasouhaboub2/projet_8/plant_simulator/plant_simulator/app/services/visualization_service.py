from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import pandas as pd

from simulation.growth_engine import GrowthEngine
from simulation.plant_generator import PlantGenerator


def generate_predictions_chart(
    predictions: pd.DataFrame, output_dir: Path, as_base64: bool
) -> tuple[str | None, str | None]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(2, 2, figsize=(10, 6), dpi=120)
    axes = ax.ravel()
    x = predictions["day_index"].to_numpy()

    axes[0].plot(x, predictions["height_cm"], color="#2d6a4f")
    axes[0].set_title("Height (cm)")
    axes[1].plot(x, predictions["leaf_count"], color="#40916c")
    axes[1].set_title("Leaf count")
    axes[2].plot(x, predictions["branch_count"], color="#1b4332")
    axes[2].set_title("Branch count")
    axes[3].plot(x, predictions["health_index"], color="#52b788")
    axes[3].set_title("Health index")

    for axis in axes:
        axis.set_xlabel("Day")
        axis.grid(alpha=0.25)

    fig.tight_layout()
    png_path = output_dir / "growth_predictions.png"
    fig.savefig(png_path, format="png")

    encoded = None
    if as_base64:
        buffer = BytesIO()
        fig.savefig(buffer, format="png")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

    plt.close(fig)
    return str(png_path.resolve()), encoded


def generate_growth_gif(predictions: pd.DataFrame, media_dir: Path, filename: str) -> str:
    import imageio.v2 as imageio
    import pyvista as pv

    media_dir.mkdir(parents=True, exist_ok=True)
    out_path = media_dir / filename

    engine = GrowthEngine(predictions=predictions, generator=PlantGenerator())
    plotter = pv.Plotter(off_screen=True, window_size=(900, 700))
    plotter.set_background("#eaf6ff")
    ground = pv.Plane(i_size=4.2, j_size=4.2, i_resolution=1, j_resolution=1)
    plotter.add_mesh(ground, color="#d8c7a1", smooth_shading=True)
    plotter.camera_position = [(2.4, -2.0, 2.0), (0, 0, 0.7), (0, 0, 1)]

    frames = []
    for day_idx in range(len(predictions)):
        engine.set_day(day_idx)
        plotter.clear_actors()
        plotter.add_mesh(ground, color="#d8c7a1", smooth_shading=True)
        for spec in engine.current_geometry():
            plotter.add_mesh(spec.mesh, color=spec.color, opacity=spec.opacity, smooth_shading=True)
        plotter.add_text(f"Day {day_idx + 1}/{len(predictions)}", position="upper_left", font_size=10, color="black")
        frames.append(plotter.screenshot(return_img=True))

    imageio.mimsave(out_path, frames, duration=0.16)
    plotter.close()
    return str(out_path.resolve())
