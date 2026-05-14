import json
import os
import warnings
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from fastapi import FastAPI, HTTPException, Request

from app.cnn_inference import load_cnn_model_if_available
from app.config import MODELS_DIR
from app.predictor import MLPRegressor
from app.routes import router
from app.utils.preprocessing import load_raw_dataset, preprocess_dataset

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")


def _resolve_model_file(name: str) -> Path:
    p = MODELS_DIR / name
    if p.exists():
        return p
    root = MODELS_DIR.parent / name
    if root.exists():
        return root
    raise FileNotFoundError(name)


def _read_csv_robust(path: Path) -> pd.DataFrame:
    try:
        sig = path.read_bytes()[:2]
        if sig == b"PK":
            return pd.read_excel(path)
    except Exception:
        pass
    attempts = [
        {"sep": ",", "encoding": "utf-8"},
        {"sep": ";", "encoding": "utf-8"},
        {"sep": ",", "encoding": "cp1252"},
        {"sep": ";", "encoding": "cp1252"},
        {"sep": ",", "encoding": "latin1"},
        {"sep": ";", "encoding": "latin1"},
    ]
    last_exc = None
    for kw in attempts:
        try:
            return pd.read_csv(path, **kw)
        except Exception as exc:
            last_exc = exc
    raise last_exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.models_loaded = False
    warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.base")
    warnings.filterwarnings("ignore", message=".*InconsistentVersionWarning.*")
    warnings.filterwarnings("ignore", message=".*serialized model.*XGBoost.*")
    warnings.filterwarnings("ignore", category=UserWarning, module="pickle", message=".*If you are loading a serialized model.*")
    warnings.filterwarnings("ignore", message=".*X does not have valid feature names.*")
    warnings.filterwarnings("ignore", message=".*physical cores.*")

    metadata_path = _resolve_model_file("metadata.json")
    app.state.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    try:
        preproc_path = _resolve_model_file("df_preprocessed.csv")
        app.state.df = _read_csv_robust(preproc_path)
    except FileNotFoundError:
        app.state.df = preprocess_dataset(load_raw_dataset())
    app.state.df_snp = app.state.df.copy()

    app.state.crossings_df = _read_csv_robust(_resolve_model_file("crossings_df.csv"))
    if "Croisement" in app.state.crossings_df.columns and "crossing_name" not in app.state.crossings_df.columns:
        app.state.crossings_df["crossing_name"] = app.state.crossings_df["Croisement"]
    elif "crossing_name" in app.state.crossings_df.columns and "Croisement" not in app.state.crossings_df.columns:
        app.state.crossings_df["Croisement"] = app.state.crossings_df["crossing_name"]

    if "parent_A" not in app.state.crossings_df.columns or "parent_B" not in app.state.crossings_df.columns:
        split_df = app.state.crossings_df["Croisement"].astype(str).str.split("  x  ", n=1, expand=True)
        app.state.crossings_df["parent_A"] = split_df[0]
        app.state.crossings_df["parent_B"] = split_df[1] if split_df.shape[1] > 1 else None

    app.state.scaler = joblib.load(_resolve_model_file("scaler.pkl"))
    app.state.ridge = joblib.load(_resolve_model_file("ridge.pkl"))
    app.state.rf = joblib.load(_resolve_model_file("rf.pkl"))
    app.state.xgb_model = joblib.load(_resolve_model_file("xgb.pkl"))
    try:
        app.state.lgb_model = joblib.load(_resolve_model_file("lgbm.pkl"))
    except Exception:
        app.state.lgb_model = None

    mlp_cfg = json.loads(_resolve_model_file("mlp_config.json").read_text(encoding="utf-8"))
    mlp = MLPRegressor(mlp_cfg["input_dim"], mlp_cfg["output_dim"], mlp_cfg.get("dropout", 0.3))
    mlp.load_state_dict(torch.load(_resolve_model_file("mlp.pt"), map_location="cpu"))
    mlp.eval()
    app.state.mlp = mlp

    app.state.clf_parent = joblib.load(_resolve_model_file("clf_parent.pkl"))
    app.state.clf_parent_features = json.loads(_resolve_model_file("clf_parent_features.json").read_text(encoding="utf-8"))
    app.state.features_parent = app.state.clf_parent_features

    app.state.cnn_model, app.state.cnn_status = load_cnn_model_if_available()
    app.state.cnn_loaded = app.state.cnn_model is not None

    snp_cols = app.state.metadata["snp_cols"]
    feature_cols = app.state.metadata.get("feature_cols", snp_cols + ["snp_activity"])
    for col in feature_cols:
        if col not in app.state.crossings_df.columns:
            app.state.crossings_df[col] = 0.0
    app.state.crossings_df[feature_cols] = app.state.crossings_df[feature_cols].fillna(0)

    try:
        app.state.pair_features = np.load(_resolve_model_file("pair_features.npy"))
    except FileNotFoundError:
        app.state.pair_features = app.state.crossings_df[feature_cols].to_numpy(dtype=float)

    app.state.feature_cols = feature_cols
    app.state.SNP_COLS = snp_cols
    app.state.models = {
        "rf": app.state.rf,
        "xgb": app.state.xgb_model,
        "lgb": app.state.lgb_model if app.state.lgb_model is not None else app.state.xgb_model,
        "ridge": app.state.ridge,
        "mlp": app.state.mlp,
    }
    app.state.shap_global = None
    app.state.rf_rank = None
    app.state.meilleur_oligo_par_snp = {}

    geno_path = MODELS_DIR.parent / "data" / "original_genotype_data.xlsx"
    app.state.snp_mapping = {}
    if geno_path.exists():
        try:
            gdf = pd.read_excel(geno_path)
            for _, r in gdf.iterrows():
                snp = str(r.get("snp", r.get("SNP", "")))
                if snp:
                    app.state.snp_mapping[snp] = {
                        "chromosome": r.get("chromosome"),
                        "position": r.get("position"),
                        "allele_A": str(r.get("allele_A", "A"))[:1],
                        "allele_B": str(r.get("allele_B", "G"))[:1],
                    }
        except Exception:
            app.state.snp_mapping = {}

    app.state.models_loaded = True

    # Optional FASTA resources
    app.state.df_agront = pd.DataFrame()
    app.state.alleles = {}
    app.state.resultats_odm = pd.DataFrame()
    yield


app = FastAPI(title="Durum Wheat Pipeline API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def ensure_loaded(request: Request, call_next):
    if not getattr(request.app.state, "models_loaded", False) and request.url.path != "/health":
        raise HTTPException(status_code=503, detail="Models are not loaded")
    return await call_next(request)


app.include_router(router)
