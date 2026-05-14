from typing import Dict

import numpy as np
import pandas as pd

from app.config import TOP_N_PER_TRAIT


def _crossing_col(crossings_df: pd.DataFrame) -> str:
    if "Croisement" in crossings_df.columns:
        return "Croisement"
    if "crossing_name" in crossings_df.columns:
        return "crossing_name"
    raise ValueError("Aucune colonne de nom de croisement trouvée (Croisement / crossing_name)")


def _sanitize_features(X: np.ndarray) -> np.ndarray:
    """
    Convertit pair_features en float64 propre.
    Gère le cas fréquent où les colonnes ont été sérialisées sous forme de string
    style '[4.7951517E-1]' (vecteur de dimension 1 entre crochets).
    """
    if X.dtype == object or X.dtype.kind in ("U", "S"):
        def _parse(v):
            s = str(v).strip().lstrip("[").rstrip("]").strip()
            return float(s.split()[0].rstrip(","))
        vfunc = np.vectorize(_parse)
        X = vfunc(X).astype(np.float64)
    else:
        X = X.astype(np.float64)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return X


def _get_estimators(app_state):
    """
    Retourne une liste de 4 estimateurs (un par trait : drought, salt, yield, disease).

    CORRECTION : priorité rf → lgb → ridge → xgb
    XGBoost (MultiOutputRegressor) retourne parfois des strings '[val]' depuis
    ses prédictions internes, ce qui fait planter SHAP.
    RandomForestRegressor natif multi-output est plus stable.
    """
    for attr in ("rf", "lgb", "ridge", "xgb"):  # ← rf EN PREMIER, xgb EN DERNIER
        m = getattr(app_state, attr, None)
        if m is None:
            models = getattr(app_state, "models", {})
            m = models.get(attr)
        if m is None:
            continue

        # MultiOutputRegressor (sklearn) expose .estimators_
        if hasattr(m, "estimators_") and len(getattr(m, "estimators_", [])) >= 4:
            return m.estimators_[:4]

        # RF natif multi-output → répéter le même modèle 4 fois
        return [m, m, m, m]

    raise AttributeError(
        "Aucun modèle compatible trouvé dans app.state (rf / lgb / ridge / xgb). "
        "Vérifiez que le startup Projet 2 a bien chargé les fichiers .pkl."
    )


def compute_shap_global(app_state, top_n: int = 10) -> Dict:
    # Si le cache contient une erreur, on le vide pour recalculer
    if app_state.shap_global is not None:
        cached = app_state.shap_global
        has_error = any(
            isinstance(v, list) and len(v) > 0 and "error" in v[0]
            for v in cached.values()
        )
        if has_error:
            app_state.shap_global = None
        else:
            return cached

    # Sanitize pair_features en place
    app_state.pair_features = _sanitize_features(app_state.pair_features)

    try:
        import shap
    except ImportError:
        app_state.shap_global = {t: [] for t in ["drought", "salt", "yield", "disease"]}
        return app_state.shap_global

    X             = app_state.pair_features
    feature_names = app_state.feature_cols
    estimators    = _get_estimators(app_state)
    out = {}

    for i, trait in enumerate(["drought", "salt", "yield", "disease"]):
        try:
            est  = estimators[i]
            expl = shap.TreeExplainer(est)
            vals = expl.shap_values(X)
            if isinstance(vals, list):
                vals = vals[0]
            # Si 3D (multioutput natif RF) → prendre output i
            if isinstance(vals, np.ndarray) and vals.ndim == 3:
                vals = vals[:, :, i]
            imp     = np.abs(vals).mean(axis=0)
            top_idx = np.argsort(imp)[::-1][:top_n]
            out[trait] = [
                {
                    "snp":        feature_names[j],
                    "importance": float(imp[j]),
                    "direction":  "positive",
                }
                for j in top_idx
            ]
        except Exception as exc:
            out[trait] = [{"error": str(exc)}]

    app_state.shap_global = out
    return out


def generate_narrative_report(
    crossing_name: str,
    estimators: list,
    pair_features: np.ndarray,
    crossings_df: pd.DataFrame,
    feature_names: list,
    crossing_col: str = "Croisement",
    top_n: int = 5,
) -> str:
    try:
        import shap
    except ImportError:
        return "⚠️ Librairie SHAP non installée. Installez-la avec : pip install shap"

    trait_labels = {
        "drought": "tolérance à la sécheresse",
        "salt":    "tolérance au sel",
        "yield":   "rendement agricole",
        "disease": "résistance aux maladies",
    }

    if crossing_col not in crossings_df.columns:
        crossing_col = _crossing_col(crossings_df)

    row = crossings_df[crossings_df[crossing_col] == crossing_name]
    if row.empty:
        row = crossings_df[
            crossings_df[crossing_col].astype(str).str.contains(
                crossing_name[:30], case=False, na=False, regex=False
            )
        ]
    if row.empty:
        return f"⚠️ Croisement '{crossing_name}' non trouvé pour l'analyse SHAP."

    idx     = int(row.index[0])
    X_clean = _sanitize_features(pair_features)
    x_input = X_clean[idx].reshape(1, -1)

    lines = [f"**Croisement analysé :** {crossing_name}\n"]
    scores_row = row.iloc[0]
    lines.append(
        f"Scores prédits — "
        f"sécheresse={float(scores_row.get('pred_drought', np.nan)):.3f}, "
        f"sel={float(scores_row.get('pred_salt', np.nan)):.3f}, "
        f"rendement={float(scores_row.get('pred_yield', np.nan)):.3f}, "
        f"maladie={float(scores_row.get('pred_disease', np.nan)):.3f}.\n"
    )

    for trait_idx, (trait, label) in enumerate(trait_labels.items()):
        try:
            est       = estimators[trait_idx]
            explainer = shap.TreeExplainer(est)
            shap_vals = explainer.shap_values(x_input)
            if isinstance(shap_vals, list):
                shap_vals = shap_vals[0]
            # Si 3D (RF multioutput natif) → prendre output trait_idx
            if isinstance(shap_vals, np.ndarray) and shap_vals.ndim == 3:
                shap_vals = shap_vals[:, :, trait_idx]
            shap_vals = shap_vals[0]
            top_idx   = np.argsort(np.abs(shap_vals))[::-1][:top_n]
            top_feats = [(feature_names[i], shap_vals[i]) for i in top_idx]
            para = f"**{label.capitalize()} :** Facteurs SNP principaux : "
            for j, (feat, val) in enumerate(top_feats):
                sens = "favorablement" if val > 0 else "défavorablement"
                para += f"{feat} ({sens})"
                para += ", " if j < len(top_feats) - 1 else ". "
            lines.append(para)
        except Exception as exc:
            lines.append(f"**{label.capitalize()} :** Analyse SHAP indisponible ({exc}).")

    lines.append(
        "\nGlobalement, ce croisement présente un score élevé grâce à la combinaison "
        "de ces marqueurs SNP, avec un bon rendement et une résistance aux maladies."
    )
    return "\n\n".join(lines)


def explain_crossing(crossing_name: str, app_state, top_n: int = TOP_N_PER_TRAIT) -> Dict:
    try:
        import shap
    except ImportError:
        return {
            "crossing_name":    crossing_name,
            "shap_global":      compute_shap_global(app_state),
            "shap_local":       {},
            "top_snps_union":   [],
            "narrative_report": "SHAP indisponible — installez shap avec : pip install shap",
        }

    cdf           = app_state.crossings_df
    crossing_col  = _crossing_col(cdf)
    feature_names = app_state.feature_cols
    estimators    = _get_estimators(app_state)

    # Recherche du croisement
    mask = cdf[crossing_col].astype(str).str.lower() == crossing_name.lower()
    if not mask.any():
        mask = cdf[crossing_col].astype(str).str.contains(
            crossing_name[:40], case=False, na=False, regex=False
        )
    if not mask.any():
        raise ValueError(
            f"crossing_name '{crossing_name}' non trouvé. "
            f"Utilisez une sous-chaîne du nom de croisement."
        )

    idx     = int(cdf.index[mask][0])
    X_clean = _sanitize_features(app_state.pair_features)
    x       = X_clean[idx: idx + 1]

    # SHAP local
    local = {}
    union = set()

    for i, trait in enumerate(["drought", "salt", "yield", "disease"]):
        try:
            est  = estimators[i]
            expl = shap.TreeExplainer(est)
            vals = expl.shap_values(x)
            if isinstance(vals, list):
                vals = vals[0]
            # Si 3D (RF multioutput natif) → prendre output i
            if isinstance(vals, np.ndarray) and vals.ndim == 3:
                vals = vals[:, :, i]
            vals    = vals[0]
            top_idx = np.argsort(np.abs(vals))[::-1][:top_n]
            items   = []
            for j in top_idx:
                union.add(feature_names[j])
                v = float(vals[j])
                items.append({
                    "snp":           feature_names[j],
                    "shap_value":    v,
                    "feature_value": float(x[0, j]),
                    "direction":     "positive" if v >= 0 else "negative",
                })
            local[trait] = items
        except Exception as exc:
            local[trait] = [{"error": str(exc)}]

    resolved_name = str(cdf.loc[idx, crossing_col])

    narrative = generate_narrative_report(
        crossing_name=resolved_name,
        estimators=estimators,
        pair_features=X_clean,
        crossings_df=app_state.crossings_df,
        feature_names=feature_names,
        crossing_col=crossing_col,
        top_n=top_n,
    )

    return {
        "crossing_name":    resolved_name,
        "shap_global":      compute_shap_global(app_state),
        "shap_local":       local,
        "top_snps_union":   sorted(union),
        "narrative_report": narrative,
    }