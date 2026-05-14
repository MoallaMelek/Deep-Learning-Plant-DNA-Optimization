"""
utils/preprocessing.py — Fonctions de stress climatique et construction des séquences LSTM

Source : notebook Étape 6 — Modélisation Phénologique G×E
Références :
  - Zheng et al. (2012) — stress multiplicatif G×E, Field Crops Research
  - Ferrise et al. (2010) — stades phénologiques blé dur Méditerranée
  - White et al. (2011) — NASA POWER pour modèles agro-climatiques
"""
import numpy as np
import re
import difflib
from typing import Optional, Tuple, Dict, List

from app.config import TRAITS, SEQ_LEN, PRED_LEN, N_STADES, DEV_CURVE


# ── Fonctions de stress climatique ─────────────────────────────────────


def compute_drought_score(T2M: float, PREC: float, GWET: float) -> float:
    heat_penalty  = np.clip((T2M - 25) / 15, 0, 1)
    water_deficit = np.clip(1 - PREC / 5.0, 0, 1)
    soil_deficit  = np.clip(1 - GWET / 0.5, 0, 1)
    stress_index  = (heat_penalty + water_deficit + soil_deficit) / 3
    return float(np.clip(1 - 0.4 * stress_index, 0, 1))


def compute_salt_score(QV2M: float, PREC: float) -> float:
    humidity_factor = np.clip(QV2M / 20.0, 0, 1)
    leaching_factor = np.clip(PREC / 5.0, 0, 1)
    salt_stress     = np.clip(humidity_factor - leaching_factor, 0, 1)
    return float(np.clip(1 - 0.3 * salt_stress, 0, 1))


def compute_yield_score(T2M: float, ALLSKY: float, PREC: float) -> float:
    heat_penalty = np.clip(abs(T2M - 20) / 20, 0, 1)
    solar_bonus  = np.clip(ALLSKY / 30.0, 0, 1)
    water_ok     = np.clip(PREC / 3.0, 0, 1)
    yield_raw    = (solar_bonus + water_ok - heat_penalty) / 2
    return float(np.clip(yield_raw, 0.1, 1))


def compute_disease_score(T2M: float, QV2M: float) -> float:
    humidity         = np.clip(QV2M / 20.0, 0, 1)
    mild_heat        = np.clip(1 - abs(T2M - 18) / 15, 0, 1)
    disease_pressure = (humidity + mild_heat) / 2
    return float(np.clip(1 - 0.35 * disease_pressure, 0.1, 1))


# ── Construction des séquences LSTM ─────────────────────────────────────


def build_lstm_input(
    row: dict,
    clim_par_stade: dict,
) -> np.ndarray:
    """
    Construit l'input LSTM (6 stades × 9 features) pour un croisement.
    Features : [T2M, PREC, ALLSKY, QV2M, GWET, pred_drought, pred_salt, pred_yield, pred_disease]

    Returns: np.ndarray shape (6, 9)
    """
    geno = np.array([
        row["pred_drought"], row["pred_salt"],
        row["pred_yield"],   row["pred_disease"],
    ])
    stade_names = list(clim_par_stade.keys())
    X = np.zeros((SEQ_LEN, 9))
    for s_idx in range(SEQ_LEN):
        c = clim_par_stade[stade_names[s_idx]]
        clim_vec = np.array([c["T2M"], c["PREC"], c["ALLSKY"], c["QV2M"], c["GWET"]])
        X[s_idx] = np.concatenate([clim_vec, geno])
    return X  # (6, 9)


def build_gxe_targets(
    row: dict,
    env_scores_par_stade: dict,
) -> np.ndarray:
    """
    Calcule la trajectoire G×E pour un croisement sur les 8 stades.
    score(t) = trait_F1_prédit × dev_curve(t) × env_stress(t)

    Returns: np.ndarray shape (8, 4) — [stade, trait]
    """
    base = np.array([
        row["pred_drought"], row["pred_salt"],
        row["pred_yield"],   row["pred_disease"],
    ])
    dev_curve = np.array(DEV_CURVE)
    mat = np.zeros((N_STADES, len(TRAITS)))
    for s_idx, stade_name in enumerate(env_scores_par_stade.keys()):
        dev_frac = dev_curve[s_idx]
        env      = env_scores_par_stade[stade_name]
        env_vec  = np.array([env["drought"], env["salt"], env["yield"], env["disease"]])
        mat[s_idx] = np.clip(base * dev_frac * env_vec, 0, 1)
    return mat  # (8, 4)


# ── Recherche de variété ─────────────────────────────────────────────────


def parse_parents_from_cross(cross_name: str) -> Tuple[Optional[str], Optional[str]]:
    """Extrait Parent A et Parent B depuis le nom d'un croisement."""
    parts = cross_name.split("  x  ")
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    parts = cross_name.split(" x ")
    if len(parts) >= 2:
        return parts[0].strip(), " x ".join(parts[1:]).strip()
    return None, None


def extract_all_parents(crossings_df) -> List[str]:
    """Extrait la liste de tous les parents uniques du dataset."""
    parents = set()
    for cross in crossings_df["Croisement"].dropna():
        pa, pb = parse_parents_from_cross(str(cross))
        if pa:
            parents.add(pa.strip())
        if pb:
            parents.add(pb.strip())
    return sorted(parents)


def find_variety_approx(
    nom: str, crossings_df, seuil: float = 0.45
) -> Tuple[Optional[str], float]:
    """
    Recherche approximative d'une variété dans le dataset.
    Returns: (nom_trouvé, score_similarité) ou (None, 0.0)
    """
    parents = extract_all_parents(crossings_df)
    nom_up  = nom.strip().upper()

    # Correspondance exacte
    exact = [v for v in parents if v.upper() == nom_up]
    if exact:
        return exact[0], 1.0

    # Correspondance partielle
    partielle = [v for v in parents if nom_up in v.upper() or v.upper() in nom_up]
    if partielle:
        return partielle[0], 0.9

    # Fuzzy matching
    proches = difflib.get_close_matches(nom_up, [v.upper() for v in parents], n=1, cutoff=seuil)
    if proches:
        match = next(v for v in parents if v.upper() == proches[0])
        ratio = difflib.SequenceMatcher(None, nom_up, proches[0]).ratio()
        return match, round(ratio, 2)

    return None, 0.0
