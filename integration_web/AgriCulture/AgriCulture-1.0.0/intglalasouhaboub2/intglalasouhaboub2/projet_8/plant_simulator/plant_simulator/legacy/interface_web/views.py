from __future__ import annotations

from pathlib import Path

import pandas as pd
from django.shortcuts import render

from data.climate_api import (
    ClimateConfig,
    TUNISIA_LATITUDE,
    TUNISIA_LONGITUDE,
    build_default_climate,
    fetch_open_meteo_climate,
)
from data.dna_loader import load_dna_sequence
from interface_web.forms import SimulationForm
from interface_web.services import generate_growth_gif, predictions_chart_base64
from ml.predict_growth import predict_growth_series
from ml.train_model import train

ARTIFACTS_DIR = Path("artifacts")


def _ensure_model(auto_train_if_missing: bool) -> str:
    model_path = ARTIFACTS_DIR / "growth_model.pt"
    if model_path.exists():
        return "Model loaded from artifacts."
    if not auto_train_if_missing:
        raise ValueError("Model missing in artifacts/. Enable auto-train or train manually first.")
    report = train(output_dir=ARTIFACTS_DIR, epochs=100)
    return f"Model trained. Scaled MSE: {report['mse_scaled']:.4f}"


def _load_climate(cleaned_data: dict) -> tuple[pd.DataFrame, str]:
    days = cleaned_data["days"]

    if cleaned_data["use_open_meteo"]:
        try:
            climate = fetch_open_meteo_climate(
                latitude=TUNISIA_LATITUDE,
                longitude=TUNISIA_LONGITUDE,
                days=days,
            )
            return climate, "Open-Meteo API (Tunisia)"
        except Exception:
            pass

    cfg = ClimateConfig(
        latitude=TUNISIA_LATITUDE,
        longitude=TUNISIA_LONGITUDE,
        days=days,
        temperature_c=cleaned_data["temperature_c"],
        humidity_pct=cleaned_data["humidity_pct"],
        precipitation_mm=cleaned_data["precipitation_mm"],
        sunlight_hours=cleaned_data["sunlight_hours"],
        wind_kph=cleaned_data["wind_kph"],
    )
    return build_default_climate(days=days, config=cfg), "Manual synthetic climate"


def home(request):
    context = {"form": SimulationForm()}
    if request.method == "POST":
        form = SimulationForm(request.POST)
        context["form"] = form
        if form.is_valid():
            try:
                dna = load_dna_sequence(
                    raw_sequence=form.cleaned_data["dna_sequence"],
                    accession=form.cleaned_data["accession"],
                )
                model_msg = _ensure_model(form.cleaned_data["auto_train_if_missing"])
                climate_df, climate_source = _load_climate(form.cleaned_data)
                predictions = predict_growth_series(dna.sequence, climate_df, model_dir=ARTIFACTS_DIR)
                chart = predictions_chart_base64(predictions)
                gif_url = None
                if form.cleaned_data["generate_gif"]:
                    gif_url = generate_growth_gif(predictions, filename="latest_growth.gif")

                context.update(
                    {
                        "success": True,
                        "model_message": model_msg,
                        "dna_source": dna.source,
                        "climate_source": climate_source,
                        "chart_base64": chart,
                        "gif_url": gif_url,
                        "summary": {
                            "final_height_cm": f"{predictions['height_cm'].iloc[-1]:.2f}",
                            "final_leaf_count": int(predictions["leaf_count"].iloc[-1]),
                            "final_branch_count": int(predictions["branch_count"].iloc[-1]),
                            "final_health": f"{predictions['health_index'].iloc[-1]:.2f}",
                        },
                        "preview_rows": predictions.head(12).to_dict(orient="records"),
                    }
                )
            except Exception as exc:
                context.update({"success": False, "error": str(exc)})
    return render(request, "interface_web/home.html", context)
