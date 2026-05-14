"""
config.py — Chemins, constantes et labels du projet G×E Blé Dur
"""
from pathlib import Path

# ── Racine du projet ────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Chemins des artefacts ───────────────────────────────────────────────
MODEL_WEIGHTS_PATH  = BASE_DIR / "models_weights" / "best_model.pth"
ARTIFACTS_PATH      = BASE_DIR / "models_weights" / "model_artifacts.pkl"

# ── Traits agronomiques ─────────────────────────────────────────────────
TRAITS = ["drought", "salt", "yield", "disease"]

TRAIT_LABELS_FR = {
    "drought": "Tolérance Sécheresse",
    "salt":    "Tolérance Salinité",
    "yield":   "Rendement (G×E)",
    "disease": "Résistance Maladies",
}

COLORS_TRAITS = {
    "drought": "#1D9E75",
    "salt":    "#378ADD",
    "yield":   "#EF9F27",
    "disease": "#D85A30",
}

# ── Stades phénologiques ────────────────────────────────────────────────
STADES_LABELS = [
    "Semis", "Germination", "Tallage", "Montaison",
    "Épiaison", "Floraison", "Remplissage", "Maturité",
]

STADES = {
    "T0_Semis":       {"doy_start": 300, "doy_end": 330, "duree_jours": 30},
    "T1_Germination": {"doy_start": 330, "doy_end": 360, "duree_jours": 30},
    "T2_Tallage":     {"doy_start": 360, "doy_end": 30,  "duree_jours": 30},
    "T3_Montaison":   {"doy_start": 30,  "doy_end": 70,  "duree_jours": 40},
    "T4_Epiaison":    {"doy_start": 70,  "doy_end": 100, "duree_jours": 30},
    "T5_Floraison":   {"doy_start": 100, "doy_end": 120, "duree_jours": 20},
    "T6_Remplissage": {"doy_start": 120, "doy_end": 150, "duree_jours": 30},
    "T7_Maturite":    {"doy_start": 150, "doy_end": 170, "duree_jours": 20},
}

# ── LSTM config ─────────────────────────────────────────────────────────
SEQ_LEN     = 6   # T0 → T5 (input)
PRED_LEN    = 2   # T6 → T7 (output)
N_STADES    = 8
N_FEATURES  = 9   # 5 climat + 4 génotype
DEV_CURVE   = [0.05, 0.15, 0.32, 0.52, 0.70, 0.85, 0.94, 1.00]

# ── Références agronomiques (ICARDA / FAO) ──────────────────────────────
RENDEMENT_MOYEN_TUNISIE = 1800   # kg/ha — FAO STAT 2022
RENDEMENT_POTENTIEL_MAX = 6500   # kg/ha — irrigué Medenine
