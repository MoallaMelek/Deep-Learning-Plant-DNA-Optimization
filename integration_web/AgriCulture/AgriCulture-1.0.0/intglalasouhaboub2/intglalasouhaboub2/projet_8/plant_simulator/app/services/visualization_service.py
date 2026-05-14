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

    media_dir.mkdir(parents=True, exist_ok=True)
    out_path = media_dir / filename

    try:
        import pyvista as pv

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
    except Exception:
        _generate_growth_gif_2d(predictions=predictions, out_path=out_path)

    return str(out_path.resolve())


def _generate_growth_gif_2d(predictions: pd.DataFrame, out_path: Path) -> None:
    import imageio.v2 as imageio
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    frames = []
    max_height = max(float(predictions["height_cm"].max()), 1.0)
    sample_count = min(len(predictions), 45)
    frame_indices = sorted(set(int(i) for i in pd.Series(range(len(predictions))).sample(sample_count, random_state=4)))
    if frame_indices[-1] != len(predictions) - 1:
        frame_indices.append(len(predictions) - 1)

    for day_idx in frame_indices:
        row = predictions.iloc[day_idx]
        height = float(row["height_cm"])
        leaves = int(row["leaf_count"])
        health = float(row["health_index"])

        fig, ax = plt.subplots(figsize=(5.4, 4.2), dpi=120)
        ax.set_facecolor("#eaf6ff")
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(0, max_height * 1.15)
        ax.axis("off")
        ax.plot([-1.4, 1.4], [0.05, 0.05], color="#b08968", linewidth=10, solid_capstyle="round")
        ax.plot([0, 0], [0.08, height], color="#2f855a", linewidth=max(3, height / 12), solid_capstyle="round")

        leaf_color = "#10b981" if health >= 0.7 else "#84cc16"
        visible_leaves = max(4, min(leaves, 28))
        for index in range(visible_leaves):
            y = 0.25 + (height * 0.82) * (index / max(1, visible_leaves - 1))
            side = -1 if index % 2 else 1
            spread = 0.22 + 0.18 * ((index % 4) / 4)
            ax.scatter(side * spread, y, s=90, c=leaf_color, alpha=0.88, marker="o")
            ax.plot([0, side * spread], [y, y + 0.05], color="#2f855a", linewidth=1.2, alpha=0.8)

        ax.text(0.03, 0.94, f"Day {day_idx + 1}/{len(predictions)}", transform=ax.transAxes, fontsize=11, weight="bold")
        ax.text(0.03, 0.88, f"Height {height:.1f} cm | Health {health:.2f}", transform=ax.transAxes, fontsize=9)
        fig.tight_layout(pad=0)

        buffer = BytesIO()
        fig.savefig(buffer, format="png")
        buffer.seek(0)
        frames.append(imageio.imread(buffer))
        plt.close(fig)

    imageio.mimsave(out_path, frames, duration=0.16)
