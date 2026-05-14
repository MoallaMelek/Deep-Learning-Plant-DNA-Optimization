from typing import Dict

import numpy as np
import pandas as pd

from app.config import CV_MODERATE, CV_STABLE, N_SIMULATIONS_DEFAULT, NOISE_STD, THRESHOLDS


def evaluate_cross_stability(
    cv_pct: float,
    cv_threshold_stable: float = CV_STABLE,
    cv_threshold_moderate: float = CV_MODERATE,
):
    if cv_pct < cv_threshold_stable:
        return "stable", "accept"
    if cv_pct < cv_threshold_moderate:
        return "moderate", "warn_xai"
    return "unstable", "trigger_step10"


def _get_model(app_state):
    """
    Résout le modèle de prédiction depuis app.state.
    Priorité : xgb → rf → lgb → ridge → mlp
    Compatible avec main_combine.py qui stocke sous state.xgb (pas state.xgb_model).
    """
    for attr in ("xgb", "rf", "lgb", "ridge"):
        m = getattr(app_state, attr, None)
        if m is not None:
            return m
    # dict models comme fallback
    models = getattr(app_state, "models", {})
    for key in ("xgb", "rf", "lgb", "ridge"):
        if models.get(key) is not None:
            return models[key]
    raise AttributeError(
        "Aucun modèle ML trouvé dans app.state. "
        "Vérifiez que le startup Projet 2 a bien chargé xgb.pkl ou rf.pkl."
    )


def simulate_crossing(
    crossing_name: str,
    app_state,
    n_simulations: int = N_SIMULATIONS_DEFAULT,
) -> Dict:
    # ── Recherche du croisement ────────────────────────────────────────────
    cdf = app_state.crossings_df

    # Colonne de nom du croisement (Croisement ou crossing_name)
    col = "Croisement" if "Croisement" in cdf.columns else "crossing_name"

    mask = cdf[col].astype(str).str.lower() == crossing_name.lower()
    if not mask.any():
        # Recherche partielle si exact non trouvé
        mask = cdf[col].astype(str).str.contains(
            crossing_name[:40], case=False, na=False, regex=False
        )
    if not mask.any():
        raise ValueError(
            f"crossing_name '{crossing_name}' non trouvé dans crossings_df. "
            f"Vérifiez l'orthographe ou utilisez une sous-chaîne du nom."
        )

    idx = cdf.index[mask][0]
    x = app_state.pair_features[idx].astype(float)

    # ── Modèle ────────────────────────────────────────────────────────────
    model = _get_model(app_state)

    # ── Simulations Monte Carlo ────────────────────────────────────────────
    sims = []
    for _ in range(n_simulations):
        noisy = x + np.random.normal(0, NOISE_STD, size=x.shape)
        pred = model.predict(noisy.reshape(1, -1))[0]
        # pred peut être un scalaire ou un array selon le modèle
        if hasattr(pred, "__len__"):
            sims.append(list(pred))
        else:
            # modèle mono-sortie → dupliquer sur les 4 traits
            sims.append([float(pred)] * 4)

    sim_df = pd.DataFrame(sims, columns=["drought", "salt", "yield", "disease"])

    # ── Statistiques par trait ─────────────────────────────────────────────
    results = {}
    cv_all = []
    for t in ["drought", "salt", "yield", "disease"]:
        m_val = float(sim_df[t].mean())
        sd    = float(sim_df[t].std())
        cv    = float((sd / m_val) * 100.0) if m_val != 0 else 999.0
        cv_all.append(cv)
        results[t] = {
            "mean":              m_val,
            "std":               sd,
            "p5":                float(np.percentile(sim_df[t], 5)),
            "p95":               float(np.percentile(sim_df[t], 95)),
            "p_threshold_pct":   float((sim_df[t] >= THRESHOLDS[t]).mean() * 100.0),
        }

    cv_pct = float(np.mean(cv_all))
    status, action = evaluate_cross_stability(cv_pct)
    msg = {
        "accept":        f"CROISEMENT STABLE — CV={cv_pct:.2f}% < {CV_STABLE}%",
        "warn_xai":      f"CROISEMENT MODÉRÉ — CV={cv_pct:.2f}% entre {CV_STABLE}% et {CV_MODERATE}%",
        "trigger_step10": f"CROISEMENT INSTABLE — CV={cv_pct:.2f}% > {CV_MODERATE}%, ODM déclenché",
    }[action]

    return {
        "crossing_name":   crossing_name,
        "n_simulations":   n_simulations,
        "results":         results,
        "series": {
            "drought": sim_df["drought"].round(6).tolist(),
            "salt":    sim_df["salt"].round(6).tolist(),
            "yield":   sim_df["yield"].round(6).tolist(),
            "disease": sim_df["disease"].round(6).tolist(),
        },
        "cv_pct":            cv_pct,
        "stability_status":  status,
        "decision": {
            "status":          status,
            "cv_pct":          cv_pct,
            "action":          action,
            "message":         msg,
            "redirect_to_odm": action == "trigger_step10",
        },
    }
