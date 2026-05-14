from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics.pairwise import cosine_similarity

from app.config import SEED, TARGET_COLS


class MLPRegressor(nn.Module):
    def __init__(self, input_dim, output_dim, dropout=0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(dropout / 2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, output_dim),
        )

    def forward(self, x):
        return self.net(x)


def _crossing_col(df: pd.DataFrame) -> str:
    return "Croisement" if "Croisement" in df.columns else "crossing_name"


def _find_row_tolerant(df: pd.DataFrame, variety_name: str) -> Optional[pd.Series]:
    if "variety_name" not in df.columns:
        return None
    name_clean = variety_name.strip().lower()
    s = df["variety_name"].astype(str).str.strip().str.lower()
    mask = s == name_clean
    if not mask.any():
        mask = s.str.contains(name_clean, na=False, regex=False)
    if not mask.any():
        return None
    return df.loc[mask].iloc[0]


def predict_one(model_name: str, X: np.ndarray, state) -> Dict[str, float]:
    model_name = (model_name or "rf").lower()
    if model_name not in state.models:
        model_name = "rf"
    model = state.models[model_name]

    if model_name == "mlp":
        X_sc = state.scaler.transform(X)
        with torch.no_grad():
            pred = model(torch.tensor(X_sc, dtype=torch.float32)).cpu().numpy()[0]
    else:
        X_in = pd.DataFrame(X, columns=state.feature_cols) if model_name == "lgb" else X
        pred = model.predict(X_in)[0]

    return {
        "drought": float(pred[0]),
        "salt": float(pred[1]),
        "yield": float(pred[2]),
        "disease": float(pred[3]),
    }


def classify_parent(variety_name: str, state) -> Dict:
    row = _find_row_tolerant(state.df_snp.reset_index(drop=False), variety_name)
    if row is None:
        return {
            "is_good_parent": False,
            "confidence": 0,
            "weak_trait": None,
            "error": "variety not found",
        }

    x_input = pd.to_numeric(row.reindex(state.features_parent), errors="coerce").fillna(0).to_numpy(dtype=float).reshape(1, -1)
    pred = int(state.clf_parent.predict(x_input)[0])
    conf = float(state.clf_parent.predict_proba(x_input)[0][1] * 100.0)
    traits = {t: float(row.get(t, 0.0)) for t in TARGET_COLS}
    weak = min(TARGET_COLS, key=lambda t: traits[t]) if pred == 0 else None
    msg = f"✅ BON PARENT — Confiance : {conf:.1f}%" if pred == 1 else f"❌ Pas recommandé comme parent. Point faible : {weak} ({traits[weak]:.3f})"
    out = {
        "variety_name": str(row["variety_name"]),
        "traits": traits,
        "is_good_parent": pred == 1,
        "confidence_pct": conf,
        "already_in_parents": bool(row.get("est_bon_parent", pred == 1)),
        "weak_trait": weak,
        "message": msg,
    }
    if pred == 0:
        alt = get_parent_alternatives(variety_name, state)
        out["alternatives"] = alt if isinstance(alt, list) else []
    return out


def get_parent_alternatives(variety_name: str, state, top_n: int = 5):
    df_snp = state.df_snp.reset_index(drop=False).copy()
    name_clean = variety_name.strip().lower()
    mask = df_snp["variety_name"].astype(str).str.strip().str.lower() == name_clean
    idx_list = df_snp.index[mask].tolist()
    if not idx_list:
        mask = df_snp["variety_name"].astype(str).str.strip().str.lower().str.contains(name_clean, na=False, regex=False)
        idx_list = df_snp.index[mask].tolist()
    if not idx_list:
        return []
    idx = idx_list[0]

    X = df_snp[state.SNP_COLS].apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy(dtype=float)
    if X.shape[0] == 0:
        return []

    sim = cosine_similarity(X[idx : idx + 1], X)[0]
    sim_df = pd.DataFrame({"variety_name": df_snp["variety_name"], "sim": sim})
    out = sim_df[sim_df.index != idx].sort_values("sim", ascending=False).head(top_n)["variety_name"].tolist()
    return out


def ensure_crossing_scores(state):
    cdf = state.crossings_df.copy()
    cdf["score_fixe"] = 0.4 * cdf["pred_drought"] + 0.3 * cdf["pred_salt"] + 0.2 * cdf["pred_yield"] + 0.1 * cdf["pred_disease"]
    if getattr(state, "rf_rank", None) is None:
        X_rank = cdf[["pred_drought", "pred_salt", "pred_yield", "pred_disease"]].to_numpy(dtype=float)
        y_rank = cdf["score_fixe"].to_numpy(dtype=float)
        state.rf_rank = RandomForestRegressor(n_estimators=200, max_depth=8, random_state=SEED).fit(X_rank, y_rank)
    cdf["score_rf"] = state.rf_rank.predict(cdf[["pred_drought", "pred_salt", "pred_yield", "pred_disease"]].to_numpy(dtype=float))
    state.crossings_df = cdf


def recommend_crossings(request_dict: Dict, state) -> List[Dict]:
    ensure_crossing_scores(state)
    cdf = state.crossings_df.copy()
    crossing_col = _crossing_col(cdf)
    mode = request_dict.get("mode", "variety")
    top_n = int(request_dict.get("top_n", 5))

    if mode == "variety":
        variety = str(request_dict.get("variety_name", "")).strip()
        subset = cdf[cdf[crossing_col].astype(str).str.contains(variety, case=False, na=False, regex=False)]
    elif mode == "profile":
        p = request_dict.get("profile", {})
        wd, ws, wy, wdi = p.get("drought", 0.25), p.get("salt", 0.25), p.get("yield", p.get("yield_score", 0.25)), p.get("disease", 0.25)
        subset = cdf.copy()
        subset["score_profile"] = wd * subset["pred_drought"] + ws * subset["pred_salt"] + wy * subset["pred_yield"] + wdi * subset["pred_disease"]
        subset = subset.sort_values("score_profile", ascending=False)
    else:
        points = cdf[["pred_drought", "pred_yield"]].to_numpy(dtype=float)
        keep = np.ones(len(points), dtype=bool)
        for i in range(len(points)):
            keep[i] = not np.any(np.all(points >= points[i], axis=1) & np.any(points > points[i], axis=1))
        subset = cdf[keep]

    subset = subset.sort_values("score_fixe", ascending=False).head(top_n)
    rows = []
    for i, r in enumerate(subset.itertuples(index=False), start=1):
        tr = {"drought": float(r.pred_drought), "salt": float(r.pred_salt), "yield": float(r.pred_yield), "disease": float(r.pred_disease)}
        rows.append(
            {
                "rank": i,
                "crossing_name": getattr(r, crossing_col),
                "pred_drought": tr["drought"],
                "pred_salt": tr["salt"],
                "pred_yield": tr["yield"],
                "pred_disease": tr["disease"],
                "score_fixe": float(r.score_fixe),
                "score_rf": float(r.score_rf),
                "score_used": float(r.score_fixe),
                "strong_trait": max(tr, key=tr.get),
                "weak_trait": min(tr, key=tr.get),
            }
        )
    return rows


def get_snp_vector(variety_name: str, state) -> pd.Series:
    row = _find_row_tolerant(state.df_snp.reset_index(drop=False), variety_name)
    if row is None:
        raise ValueError(f"variety not found: {variety_name}")
    vec = pd.to_numeric(row.reindex(state.feature_cols), errors="coerce").fillna(0.0)
    vec.index = state.feature_cols
    return vec


def predict_crossing(feat_a: pd.Series, feat_b: pd.Series, state, model_name: str = "rf", n_simulations: int = 1) -> Dict:
    snps_a = feat_a[state.SNP_COLS].to_numpy(dtype=float)
    snps_b = feat_b[state.SNP_COLS].to_numpy(dtype=float)
    rng = np.random.default_rng(SEED)
    mask = rng.integers(0, 2, size=len(state.SNP_COLS)).astype(bool)
    snps = np.where(mask, snps_a, snps_b)
    act = float((feat_a["snp_activity"] + feat_b["snp_activity"]) / 2.0)
    X = np.append(snps, act).reshape(1, -1)

    if model_name == "ensemble":
        preds = [predict_one(m, X, state) for m in ["ridge", "rf", "xgb", "lgb", "mlp"] if m in state.models]
        mean = {k: float(np.mean([p[k] for p in preds])) for k in ["drought", "salt", "yield", "disease"]}
    else:
        mean = predict_one(model_name, X, state)
    score = float(sum(mean.values()) / 4.0)
    return {**mean, "score_composite": score}


def simulate_montecarlo(feat_a: pd.Series, feat_b: pd.Series, n_sim: int, model_name: str, seed: int, state):
    rng = np.random.default_rng(seed)
    results = []
    snps_a = feat_a[state.SNP_COLS].to_numpy(dtype=float)
    snps_b = feat_b[state.SNP_COLS].to_numpy(dtype=float)
    act = float((feat_a["snp_activity"] + feat_b["snp_activity"]) / 2.0)
    for _ in range(n_sim):
        mask = rng.integers(0, 2, size=len(state.SNP_COLS)).astype(bool)
        snps = np.where(mask, snps_a, snps_b)
        X_desc = np.append(snps, act).reshape(1, -1)
        preds = predict_one(model_name, X_desc, state)
        score = float(sum(preds.values()) / 4.0)
        results.append({**preds, "score_composite": score})

    df_res = pd.DataFrame(results)
    return {
        "n_simulations": n_sim,
        "mean": df_res.mean().round(4).to_dict(),
        "std": df_res.std().round(4).to_dict(),
        "min": df_res.min().round(4).to_dict(),
        "max": df_res.max().round(4).to_dict(),
        "p5": df_res.quantile(0.05).round(4).to_dict(),
        "p95": df_res.quantile(0.95).round(4).to_dict(),
        "distribution": {col: df_res[col].round(3).tolist() for col in ["drought", "salt", "yield", "disease", "score_composite"]},
    }

