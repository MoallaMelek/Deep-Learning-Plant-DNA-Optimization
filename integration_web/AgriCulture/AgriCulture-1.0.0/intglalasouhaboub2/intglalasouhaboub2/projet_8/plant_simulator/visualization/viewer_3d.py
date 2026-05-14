"""Interactive 3D viewer for animated plant growth."""

from __future__ import annotations

from typing import List

import pyvista as pv

from simulation.growth_engine import GrowthEngine
from simulation.plant_generator import MeshSpec


class PlantGrowthViewer:
    def __init__(self, engine: GrowthEngine, interval_ms: int = 180):
        self.engine = engine
        self.interval_ms = interval_ms
        self.plotter = pv.Plotter(window_size=(1300, 850))
        self._plant_actors: List = []
        self._hud_actor = None
        self._slider_updating = False

    def _add_static_scene(self) -> None:
        self.plotter.set_background("#eaf6ff")
        ground = pv.Plane(i_size=4.2, j_size=4.2, i_resolution=1, j_resolution=1)
        self.plotter.add_mesh(ground, color="#d8c7a1", smooth_shading=True)
        self.plotter.add_axes()
        self.plotter.camera_position = [(2.4, -2.0, 2.0), (0, 0, 0.7), (0, 0, 1)]

    def _render_day(self) -> None:
        for actor in self._plant_actors:
            self.plotter.remove_actor(actor, reset_camera=False, render=False)
        self._plant_actors.clear()

        meshes: List[MeshSpec] = self.engine.current_geometry()
        for spec in meshes:
            actor = self.plotter.add_mesh(
                spec.mesh,
                color=spec.color,
                opacity=spec.opacity,
                smooth_shading=True,
                render=False,
            )
            self._plant_actors.append(actor)

        row = self.engine.current_row()
        hud = (
            f"Day {self.engine.current_day + 1}/{self.engine.max_day + 1} | "
            f"Height: {row['height_cm']:.1f} cm | Leaves: {int(row['leaf_count'])} | "
            f"Branches: {int(row['branch_count'])} | Health: {row['health_index']:.2f} | "
            f"State: {'Play' if self.engine.playing else 'Pause'}"
        )
        if self._hud_actor is not None:
            self.plotter.remove_actor(self._hud_actor, render=False)
        self._hud_actor = self.plotter.add_text(hud, position="upper_left", font_size=11, color="black")
        self.plotter.render()

    def _on_slider(self, value: float) -> None:
        if self._slider_updating:
            return
        self.engine.set_day(int(round(value)))
        self.engine.playing = False
        self._render_day()

    def _on_timer(self, _step: int) -> None:
        if not self.engine.playing:
            return
        self.engine.next_day()
        self._render_day()

    def _setup_interactions(self) -> None:
        self.plotter.add_key_event("space", self._toggle_play)
        self.plotter.add_key_event("Right", self._step_forward)
        self.plotter.add_key_event("Left", self._step_back)
        self.plotter.add_key_event("r", self._restart)
        self.plotter.add_slider_widget(
            self._on_slider,
            rng=[0, self.engine.max_day],
            value=0,
            title="Timeline (Day Index)",
            pointa=(0.025, 0.08),
            pointb=(0.32, 0.08),
            style="modern",
        )
        self.plotter.add_timer_event(max_steps=500_000, duration=self.interval_ms, callback=self._on_timer)

    def _toggle_play(self) -> None:
        self.engine.toggle_play()
        self._render_day()

    def _step_forward(self) -> None:
        self.engine.playing = False
        self.engine.next_day()
        self._render_day()

    def _step_back(self) -> None:
        self.engine.playing = False
        self.engine.prev_day()
        self._render_day()

    def _restart(self) -> None:
        self.engine.set_day(0)
        self.engine.playing = False
        self._render_day()

    def show(self) -> None:
        self._add_static_scene()
        self._setup_interactions()
        self._render_day()
        self.plotter.show(title="Plant Growth Simulator (Space: play/pause)")
