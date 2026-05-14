from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Optional

import pandas as pd
import pyvista as pv
from django.conf import settings

from simulation.growth_engine import GrowthEngine
from simulation.plant_generator import PlantGenerator

def predictions_chart_base64(predictions: pd.DataFrame) -> str:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

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

    for a in axes:
        a.set_xlabel("Day")
        a.grid(alpha=0.25)

    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generate_growth_gif(predictions: pd.DataFrame, filename: str = "growth.gif") -> Optional[str]:
    try:
        import imageio.v2 as imageio

        media_dir = Path(settings.MEDIA_ROOT)
        media_dir.mkdir(parents=True, exist_ok=True)
        out_path = media_dir / filename

        engine = GrowthEngine(predictions=predictions, generator=PlantGenerator())
        plotter = pv.Plotter(off_screen=True, window_size=(900, 700))
        plotter.set_background("#eaf6ff")
        ground = pv.Plane(i_size=4.2, j_size=4.2, i_resolution=1, j_resolution=1)
        plotter.add_mesh(ground, color="#d8c7a1", smooth_shading=True)
        plotter.camera_position = [(2.4, -2.0, 2.0), (0, 0, 0.7), (0, 0, 1)]

        frames = []
        for d in range(len(predictions)):
            engine.set_day(d)
            plotter.clear_actors()
            plotter.add_mesh(ground, color="#d8c7a1", smooth_shading=True)
            for spec in engine.current_geometry():
                plotter.add_mesh(spec.mesh, color=spec.color, opacity=spec.opacity, smooth_shading=True)
            plotter.add_text(f"Day {d + 1}/{len(predictions)}", position="upper_left", font_size=10, color="black")
            frames.append(plotter.screenshot(return_img=True))

        imageio.mimsave(out_path, frames, duration=0.16)
        plotter.close()
        return f"{settings.MEDIA_URL}{filename}"
    except Exception:
        return None
