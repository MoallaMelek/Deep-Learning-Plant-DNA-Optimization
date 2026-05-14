from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

# Data
EXCEL_PATH = str(BASE_DIR / "data" / "predictions_croisements.xlsx")

# Scenarios & horizons
SCENARIOS = ["normal", "secheresse", "canicule", "maladie", "optimal"]
HORIZONS = ["1_semaine", "1_mois", "3_mois", "6_mois", "1_an"]
HORIZON_DAYS = {
    "1_semaine": 7,
    "1_mois": 30,
    "3_mois": 90,
    "6_mois": 180,
    "1_an": 365,
}

# PCSE / WOFOST
# If not set or file missing, /predict must return 503 ("WOFOST unavailable").
PCSE_DB_PATH = str(BASE_DIR / "models_weights" / "pcse.db")

