"""Tkinter interface for running training and growth simulation."""

from __future__ import annotations

from pathlib import Path
from tkinter import END, Button, Checkbutton, Entry, Frame, IntVar, Label, Spinbox, Text, Tk
from tkinter import messagebox

from data.climate_api import (
    ClimateConfig,
    TUNISIA_LATITUDE,
    TUNISIA_LONGITUDE,
    build_default_climate,
    fetch_open_meteo_climate,
)
from data.dna_loader import EXAMPLE_DNA_SEQUENCE, load_dna_sequence
from ml.predict_growth import predict_growth_series
from ml.train_model import train
from simulation.growth_engine import GrowthEngine
from simulation.plant_generator import PlantGenerator
from visualization.viewer_3d import PlantGrowthViewer


class PlantSimulatorApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("Plant Growth Simulator")
        self.artifacts_dir = Path("artifacts")
        self._build_ui()

    def _build_ui(self) -> None:
        main = Frame(self.root, padx=12, pady=12)
        main.grid(row=0, column=0, sticky="nsew")

        Label(main, text="DNA Sequence").grid(row=0, column=0, sticky="w")
        self.dna_text = Text(main, width=90, height=8)
        self.dna_text.grid(row=1, column=0, columnspan=4, pady=(4, 8))
        self.dna_text.insert(END, EXAMPLE_DNA_SEQUENCE)

        Label(main, text="NCBI Accession (optional)").grid(row=2, column=0, sticky="w")
        self.accession_entry = Entry(main, width=26)
        self.accession_entry.grid(row=2, column=1, sticky="w", padx=(6, 12))

        Label(main, text="Duration (days)").grid(row=2, column=2, sticky="e")
        self.days_spin = Spinbox(main, from_=30, to=120, width=6)
        self.days_spin.grid(row=2, column=3, sticky="w", padx=(6, 0))
        self.days_spin.delete(0, END)
        self.days_spin.insert(0, "60")

        self.auto_climate_var = IntVar(value=1)
        self.auto_climate_check = Checkbutton(main, text="Fetch climate from Open-Meteo", variable=self.auto_climate_var)
        self.auto_climate_check.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 6))

        Label(main, text="Manual Climate (used when API disabled/fails)").grid(row=4, column=0, sticky="w", pady=(8, 0))
        Label(main, text="Temp C").grid(row=5, column=0, sticky="w")
        self.temp_entry = Entry(main, width=10)
        self.temp_entry.grid(row=5, column=1, sticky="w")
        self.temp_entry.insert(0, "22")

        Label(main, text="Humidity %").grid(row=5, column=2, sticky="e")
        self.humidity_entry = Entry(main, width=10)
        self.humidity_entry.grid(row=5, column=3, sticky="w")
        self.humidity_entry.insert(0, "60")

        Label(main, text="Precip mm").grid(row=6, column=0, sticky="w")
        self.precip_entry = Entry(main, width=10)
        self.precip_entry.grid(row=6, column=1, sticky="w")
        self.precip_entry.insert(0, "1.5")

        Label(main, text="Sunlight h").grid(row=6, column=2, sticky="e")
        self.sun_entry = Entry(main, width=10)
        self.sun_entry.grid(row=6, column=3, sticky="w")
        self.sun_entry.insert(0, "8")

        Label(main, text="Wind kph").grid(row=7, column=0, sticky="w")
        self.wind_entry = Entry(main, width=10)
        self.wind_entry.grid(row=7, column=1, sticky="w")
        self.wind_entry.insert(0, "10")

        self.status = Label(main, text="Status: Ready", anchor="w")
        self.status.grid(row=8, column=0, columnspan=4, sticky="we", pady=(10, 10))

        Button(main, text="Train Model", command=self.on_train, width=18).grid(row=9, column=0, pady=(2, 0))
        Button(main, text="Simulate Growth", command=self.on_simulate, width=18).grid(row=9, column=1, pady=(2, 0))

    def _set_status(self, text: str) -> None:
        self.status.config(text=f"Status: {text}")
        self.root.update_idletasks()

    def _ensure_model(self) -> None:
        model_file = self.artifacts_dir / "growth_model.pt"
        if model_file.exists():
            return
        self._set_status("Training model (first run)...")
        train(output_dir=self.artifacts_dir, epochs=100)

    def _load_dna(self):
        dna_text = self.dna_text.get("1.0", END).strip()
        accession = self.accession_entry.get().strip() or None
        return load_dna_sequence(raw_sequence=dna_text, accession=accession)

    def _build_manual_climate(self, days: int):
        cfg = ClimateConfig(
            latitude=TUNISIA_LATITUDE,
            longitude=TUNISIA_LONGITUDE,
            days=days,
            temperature_c=float(self.temp_entry.get()),
            humidity_pct=float(self.humidity_entry.get()),
            precipitation_mm=float(self.precip_entry.get()),
            sunlight_hours=float(self.sun_entry.get()),
            wind_kph=float(self.wind_entry.get()),
        )
        return build_default_climate(days=days, config=cfg)

    def _load_climate(self, days: int):
        if self.auto_climate_var.get() == 1:
            try:
                self._set_status("Fetching climate from Open-Meteo (Tunisia)...")
                return fetch_open_meteo_climate(
                    latitude=TUNISIA_LATITUDE,
                    longitude=TUNISIA_LONGITUDE,
                    days=days,
                )
            except Exception as exc:
                self._set_status("Open-Meteo unavailable, using manual synthetic climate.")
                print(f"[warning] Open-Meteo fetch failed: {exc}")
        return self._build_manual_climate(days)

    def on_train(self) -> None:
        try:
            self._set_status("Training model on CPU...")
            report = train(output_dir=self.artifacts_dir, epochs=120)
            self._set_status(f"Training done. Scaled MSE={report['mse_scaled']:.4f}")
        except Exception as exc:
            messagebox.showerror("Training Error", str(exc))
            self._set_status("Training failed.")

    def on_simulate(self) -> None:
        try:
            days = int(self.days_spin.get())
            dna = self._load_dna()
            self._ensure_model()
            climate = self._load_climate(days)
            self._set_status("Running model predictions...")
            predictions = predict_growth_series(dna.sequence, climate, model_dir=self.artifacts_dir)

            self._set_status("Opening 3D viewer...")
            engine = GrowthEngine(predictions=predictions, generator=PlantGenerator())
            viewer = PlantGrowthViewer(engine=engine)
            viewer.show()
            self._set_status("Simulation completed.")
        except Exception as exc:
            messagebox.showerror("Simulation Error", str(exc))
            self._set_status("Simulation failed.")


def run_app() -> None:
    root = Tk()
    app = PlantSimulatorApp(root)
    root.mainloop()
