"""State engine that advances plant growth across predicted days."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from simulation.plant_generator import PlantGenerator


@dataclass
class GrowthEngine:
    predictions: pd.DataFrame
    generator: PlantGenerator
    current_day: int = 0
    playing: bool = True

    @property
    def max_day(self) -> int:
        return max(0, len(self.predictions) - 1)

    def set_day(self, day: int) -> None:
        self.current_day = int(max(0, min(self.max_day, day)))

    def next_day(self) -> None:
        if self.current_day < self.max_day:
            self.current_day += 1
        else:
            self.playing = False

    def prev_day(self) -> None:
        self.current_day = max(0, self.current_day - 1)

    def toggle_play(self) -> None:
        self.playing = not self.playing

    def current_row(self):
        return self.predictions.iloc[self.current_day]

    def current_geometry(self):
        return self.generator.build_day_geometry(self.current_row())
