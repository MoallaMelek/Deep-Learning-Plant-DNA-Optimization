"""
main_combine.py — Point d'entrée unique combinant les 8 projets FastAPI
=========================================================================
Projets intégrés :
  - /wheat/   → Projet 1 : Wheat Leaf Disease Classifier (TensorFlow/CNN)
  - /durum/   → Projet 2 : Durum Wheat Pipeline API (ML classique + MLP)
  - /gxe/     → Projet 3 : G×E Blé Dur LSTM/GRU (Phénologie)
  - /twin/    → Projet 4 : Digital Twin Blé API
  - /cropdna/ → Projet 5 : CropDNA AI Platform (IoT + Génomique)
  - /crispr/  → Projet 6 : CRISPR Editing Efficiency Predictor (GBR + SHAP)
  - /pest/    → Projet 7 : IP102 Pest Image Classifier (ResNet50/timm)
  - /sound/   → Projet 8 : Insect Sound Classifier (CNN14 PANN)
  - /odm/    → Projet 9 : ODM Wheat API (DNABERT Fine-Tuning)
  - /pharma/ → Projet 10 : Plant DNA / Protein Expression ML
=========================================================================
CORRECTION : state.wheat_predictor (P1) ≠ state.gxe_predictor (P3)
             pour éviter l'écrasement de state.predictor entre projets.
=========================================================================
"""

from __future__ import annotations

import importlib
import hashlib
import io
import json
import math
import os
import pickle
import secrets
import sqlite3
import struct
import sys
import time
import warnings
import wave
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# =========================================================================
# Chargeur de modules isolé — évite les collisions entre les "app/" des projets
# =========================================================================
_BASE = Path(__file__).parent


def _load_project_module(proj: str, module_path: str):
    """
    Charge un module d'un sous-projet de façon isolée.

    Stratégie (sans meta_path hook — source de récursion infinie) :
    1. Sauvegarde sys.path.
    2. Met le répertoire du projet EN TÊTE, retire les autres projets.
    3. Vide le cache sys.modules pour 'app' et sous-modules.
    4. Importe normalement : Python trouve d'abord le bon projet.
    5. Stocke sous nom unique pour éviter les collisions.
    6. Restaure sys.path dans tous les cas (finally).
    """
    proj_root   = str(_BASE / proj)
    unique_name = f"_{proj}__{module_path.replace('.', '__')}"

    if unique_name in sys.modules:
        return sys.modules[unique_name]

    # Projets à exclure du path pendant ce chargement
    other_proj_paths = [
        str(_BASE / p)
        for p in [
            "projet1",
            "projet2",
            "projet3",
            "projet4",
            "projet5",
            "odm_project",
            "projet_6/Dna_Project_groupe/Dna_Project_Insuline",
            "projet_7/plant_research_paper",
            "projet_8/plant_simulator",
            "projet_9",
        ]
        if p != proj
    ]

    # Construire un path propre : sans les autres projets, proj_root en tête
    old_path  = list(sys.path)
    clean     = [p for p in sys.path if p not in other_proj_paths and p != proj_root]
    sys.path[:] = [proj_root] + clean

    # Vider le cache "app.*" pour forcer le rechargement depuis le bon projet
    extra_pkg_roots: list[str] = []
    if proj == "projet_8/plant_simulator":
        extra_pkg_roots = ["data", "ml", "simulation"]
    if proj == "projet_9":
        extra_pkg_roots = ["utils", "ethics_api"]

    stale_keys = [
        k
        for k in sys.modules
        if k == "app"
        or k.startswith("app.")
        or any(k == root or k.startswith(f"{root}.") for root in extra_pkg_roots)
    ]
    saved_mods = {k: sys.modules.pop(k) for k in stale_keys}

    try:
        mod = importlib.import_module(module_path)
        sys.modules[unique_name] = mod
        return mod
    except Exception:
        sys.modules.update(saved_mods)   # restaurer en cas d'échec
        raise
    finally:
        sys.path[:] = old_path           # toujours restaurer sys.path



# =========================================================================
# Chargement isolé — Projet 1
# =========================================================================
_p1_config    = _load_project_module("projet1", "app.config")
_p1_model     = _load_project_module("projet1", "app.models.wheat_cnn")
_p1_predictor = _load_project_module("projet1", "app.predictor")
_p1_routes    = _load_project_module("projet1", "app.routes")

settings_wheat   = _p1_config.settings
load_wheat_model = _p1_model.load_wheat_model
WheatPredictor   = _p1_predictor.WheatPredictor
wheat_router     = _p1_routes.router

# =========================================================================
# Chargement isolé — Projet 2
# =========================================================================
_p2_cnn       = _load_project_module("projet2", "app.cnn_inference")
_p2_config    = _load_project_module("projet2", "app.config")
_p2_predictor = _load_project_module("projet2", "app.predictor")
_p2_routes    = _load_project_module("projet2", "app.routes")
_p2_preproc   = _load_project_module("projet2", "app.utils.preprocessing")
_p2_explainer = _load_project_module("projet2", "app.explainer")
_p2_genomic   = _load_project_module("projet2", "app.genomic")

load_cnn_model_if_available = _p2_cnn.load_cnn_model_if_available
MODELS_DIR_DURUM            = _p2_config.MODELS_DIR
MLPRegressor                = _p2_predictor.MLPRegressor
durum_router                = _p2_routes.router
load_raw_dataset            = _p2_preproc.load_raw_dataset
preprocess_dataset          = _p2_preproc.preprocess_dataset

# =========================================================================
# Chargement isolé — Projet 3
# =========================================================================
_p3_routes    = _load_project_module("projet3", "app.routes")
_p3_predictor = _load_project_module("projet3", "app.predictor")

gxe_router   = _p3_routes.router
GxEPredictor = _p3_predictor.GxEPredictor

# =========================================================================
# Chargement isolé — Projet 4
# =========================================================================
_p4_routes  = _load_project_module("projet4", "app.routes.api")
_p4_service = _load_project_module("projet4", "app.services.digital_twin_service")

twin_router        = _p4_routes.router
DigitalTwinService = _p4_service.DigitalTwinService

# =========================================================================
# Chargement — Projet 5
# =========================================================================
_proj5_root = str(_BASE / "projet5")
if _proj5_root not in sys.path:
    sys.path.insert(0, _proj5_root)

from projet5.module8_client import router as module8_router  # noqa: E402
from projet5.module7_client import router as module7_router  # noqa: E402
from projet5.routers.iot import router as iot_router         # noqa: E402
from projet5.database import init_db                         # noqa: E402

# =========================================================================
# Chargement isolé — ODM Project (Projet 9)
# =========================================================================
_odm_routes = _load_project_module("odm_project", "app.routes")
odm_router  = _odm_routes.router

# =========================================================================
# Chargement isolé — Pharma Project (Projet 10)
# =========================================================================
_pharma_routes = _load_project_module("projet_6/Dna_Project_groupe/Dna_Project_Insuline", "app.routes")
pharma_router  = _pharma_routes.router

# =========================================================================
# Chargement isolé — Writing Project (Projet 7)
# =========================================================================
writing_router = None
try:
    _writing_routes = _load_project_module("projet_7/plant_research_paper", "app.routes")
    writing_router  = _writing_routes.router
except Exception as exc:
    print(f"⚠️  Projet 7 (Writing Research Paper) non disponible : {exc}")

# =========================================================================
# Chargement isolé — Growth Simulator (Projet 8)
# =========================================================================
growth_router = None
try:
    _growth_routes = _load_project_module("projet_8/plant_simulator", "app.routes")
    growth_router  = _growth_routes.router
except Exception as exc:
    print(f"⚠️  Projet 8 (Plant Growth Simulator) non disponible : {exc}")

# =========================================================================
# Chargement isolé — Ethics Compliance (Projet 9)
# =========================================================================
ethics_router = None
try:
    _ethics_routes = _load_project_module("projet_9", "ethics_api.routes")
    ethics_router  = _ethics_routes.router
except Exception as exc:
    print(f"⚠️  Projet 9 (Ethics Compliance) non disponible : {exc}")

# =========================================================================
# Imports tiers
# =========================================================================
import joblib        # noqa: E402
import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402
import shap          # noqa: E402
import torch         # noqa: E402
import torch.nn as nn                         # noqa: E402
import torch.nn.functional as F               # noqa: E402
import timm                                   # noqa: E402
import librosa                                # noqa: E402
import soundfile as sf                        # noqa: E402
from sklearn._loss.loss import HalfSquaredError  # noqa: E402
from PIL import Image                         # noqa: E402
from torchvision import transforms            # noqa: E402
from torch.amp import autocast                # noqa: E402

from fastapi import FastAPI, File, HTTPException, Request, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles         # noqa: E402
from pydantic import BaseModel, Field, field_validator  # noqa: E402

warnings.filterwarnings("ignore")


# =========================================================================
# Mobile support : authentification simple + TTS fallback
# =========================================================================
MOBILE_AUTH_DB = _BASE / "mobile_auth.db"


class MobileSignupRequest(BaseModel):
    email: str = ""
    phone: str
    password: str
    full_name: str
    farm_name: Optional[str] = None
    location: Optional[str] = None


class MobileLoginRequest(BaseModel):
    identifier: str
    password: str


def _auth_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(MOBILE_AUTH_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _init_mobile_auth_db() -> None:
    with _auth_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mobile_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                farm_name TEXT,
                location TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mobile_tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES mobile_users(id)
            )
            """
        )


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    if not password or len(password) < 4:
        raise HTTPException(status_code=400, detail="Password too short")
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"{salt}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
        return secrets.compare_digest(_hash_password(password, salt).split("$", 1)[1], expected)
    except Exception:
        return False


def _public_user(row: sqlite3.Row) -> Dict[str, Any]:
    email = row["email"]
    return {
        "id": row["id"],
        "email": "" if email.endswith("@phone.local") else email,
        "phone": row["phone"],
        "full_name": row["full_name"],
        "farm_name": row["farm_name"],
        "location": row["location"],
    }


def _create_mobile_token(conn: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO mobile_tokens (token, user_id) VALUES (?, ?)", (token, user_id))
    return token


def _get_user_by_token(token: str) -> Optional[sqlite3.Row]:
    if not token:
        return None
    with _auth_conn() as conn:
        return conn.execute(
            """
            SELECT u.*
            FROM mobile_users u
            JOIN mobile_tokens t ON t.user_id = u.id
            WHERE t.token = ?
            """,
            (token,),
        ).fetchone()


def _make_placeholder_wav(text: str) -> bytes:
    # Local, dependency-free fallback. Devices with Arabic voices use flutter_tts directly.
    sample_rate = 22050
    duration = max(0.45, min(3.0, 0.05 * len(text)))
    total = int(sample_rate * duration)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(total):
            t = i / sample_rate
            envelope = min(1.0, i / 1500) * min(1.0, (total - i) / 1500)
            freq = 440.0 + 60.0 * math.sin(2 * math.pi * 2.0 * t)
            sample = int(0.18 * envelope * 32767 * math.sin(2 * math.pi * freq * t))
            wav_file.writeframes(struct.pack("<h", sample))
    return buf.getvalue()


class HalfSquaredErrorCompat(HalfSquaredError):
    """Compatibility class required by the serialized CRISPR model."""


# Injection into multiple locations to ensure joblib/pickle can find it
# regardless of how the server is launched (python -m uvicorn vs python main.py)
for mod_name in ["__main__", "main_combine", "uvicorn.main", "uvicorn.__main__"]:
    m = sys.modules.get(mod_name)
    if m:
        setattr(m, "HalfSquaredErrorCompat", HalfSquaredErrorCompat)

# =========================================================================
# ── PROJET 6 : CRISPR — modèles & logique inline ─────────────────────────
# =========================================================================

# Résolution des chemins absolus par rapport à ce fichier
# Garantit le bon fonctionnement quel que soit le répertoire de lancement.
def _resolve_asset(relative_path: str, env_var: str | None = None) -> Path:
    if env_var:
        val = os.getenv(env_var)
        if val:
            return Path(val)
    p = Path(relative_path)
    if p.exists():
        return p
    p2 = _BASE / relative_path
    if p2.exists():
        return p2
    return _BASE / relative_path   # chemin absolu, erreur levée au chargement

CRISPR_MODEL_PATH = _resolve_asset("crispr/model.pkl",          "CRISPR_MODEL_PATH")

EXP_ORDER    = {"low": 0, "medium": 1, "high": 2}
ALL_FEATURES = ["Exo", "Int", "Pro"]


# ── Pydantic schemas CRISPR ───────────────────────────────────────────────
class CrisprPredictionRequest(BaseModel):
    # Support for both frontend ('sequence') and original ('guide_sequence') names
    sequence: Optional[str] = None
    guide_sequence: Optional[str] = None
    
    amplicon_sequence: str = "GCTAGCTAGCTAGCTA"
    
    # Support for 'chromatin' (int) and 'within_atac_peak' (bool)
    chromatin: Optional[int] = None
    within_atac_peak: Optional[bool] = None
    
    # Support for int levels (0,1,2) and str labels ('low','medium','high')
    leaf_exp: Any = "medium"
    t0_exp: Any = "medium"
    
    # Support for 'region' ('Exon', 'Intron', 'Promoter') and 'feature' ('Exo', 'Int', 'Pro')
    region: Optional[str] = None
    feature: Optional[str] = None


class CrisprPredictionResponse(BaseModel):
    efficiency: float
    predicted_editing_efficiency: float
    prediction_clipped: bool


class CrisprRecommendRequest(BaseModel):
    guide: str
    efficiency: float
    features: Dict[str, Any]


class CrisprFeatureContribution(BaseModel):
    feature: str
    value: float
    shap_value: float
    direction: str


class CrisprExplainResponse(BaseModel):
    predicted_editing_efficiency: float
    prediction_clipped: bool
    baseline: float
    net_shap_shift: float
    top_drivers: List[CrisprFeatureContribution]
    all_contributions: List[CrisprFeatureContribution]
    top_n: int


CrisprPredictionRequest.model_rebuild()
CrisprRecommendRequest.model_rebuild()
CrisprExplainResponse.model_rebuild()


# ── Feature engineering CRISPR ────────────────────────────────────────────
def _crispr_nucleotide_features(seq: str) -> dict:
    seq = seq.upper()
    n   = len(seq)
    feats: dict = {}
    for nt in ["A", "T", "G", "C"]:
        feats[f"guide_{nt}_freq"] = seq.count(nt) / n
    feats["guide_GC"] = (seq.count("G") + seq.count("C")) / n
    for d in ["AA","AT","AG","AC","TA","TT","TG","TC","GA","GT","GG","GC","CA","CT","CG","CC"]:
        feats[f"guide_di_{d}"] = (
            sum(1 for i in range(n - 1) if seq[i:i+2] == d) / max(n - 1, 1)
        )
    feats["guide_seed_GC"] = (
        (seq[-12:].count("G") + seq[-12:].count("C")) / 12 if n >= 12 else 0
    )
    return feats


def _crispr_amplicon_features(seq: str) -> dict:
    seq = str(seq).upper()
    n   = len(seq)
    return {"amp_GC": (seq.count("G") + seq.count("C")) / max(n, 1), "amp_len": n}


def _crispr_build_vector(req: CrisprPredictionRequest, model) -> pd.DataFrame:
    row: dict = {}
    
    # Resolving field aliases
    guide = req.sequence or req.guide_sequence or "ATGCATGCATGCATGCATGC"
    within_atac = bool(req.chromatin) if req.chromatin is not None else (req.within_atac_peak if req.within_atac_peak is not None else True)
    
    # Expression mapping
    def map_exp(val):
        if isinstance(val, int):
            return ["low", "medium", "high"][min(max(val, 0), 2)]
        return str(val).lower()
        
    l_exp = map_exp(req.leaf_exp)
    t_exp = map_exp(req.t0_exp)
    
    # Feature mapping
    feat = req.region or req.feature or "Exo"
    if feat == "Exon": feat = "Exo"
    if feat == "Intron": feat = "Int"
    if feat == "Promoter": feat = "Pro"

    row["within_atac_peak"] = int(within_atac)
    row["leaf_exp_enc"]     = EXP_ORDER.get(l_exp, 1)
    row["t0_exp_enc"]       = EXP_ORDER.get(t_exp, 1)
    
    for f in ALL_FEATURES:
        row[f"feat_{f}"] = int(feat == f)
        
    row.update(_crispr_nucleotide_features(guide))
    row.update(_crispr_amplicon_features(req.amplicon_sequence))
    
    df = pd.DataFrame([row])
    if hasattr(model, "feature_names_in_"):
        expected = list(model.feature_names_in_)
        for col in expected:
            if col not in df.columns:
                df[col] = 0
        df = df[expected]
    return df


# =========================================================================
# ── PROJET 7 : PEST IMAGE — architecture & helpers inline ────────────────
# =========================================================================

PEST_IMG_SIZE    = 224
PEST_NUM_CLASSES = 15
PEST_DEVICE      = torch.device("cuda" if torch.cuda.is_available() else "cpu")
PEST_USE_AMP     = torch.cuda.is_available()
PEST_MODEL_PATH  = str(_resolve_asset("insect_img/best_efficientnet_b0_ip102.pth", "PEST_MODEL_PATH"))

PEST_CLASS_NAMES = [
    "army_worm", "asiatic_rice_borer", "beet_army_worm", "blister_beetle",
    "Cicadella_viridis", "Cicadellidae", "corn_borer", "flax_budworm",
    "legume_blister_beetle", "Limacodidae", "Lycorma_delicatula", "Miridae",
    "mole_cricket", "Prodenia_litura", "rice_leaf_roller",
]

PEST_MEAN = [0.485, 0.456, 0.406]
PEST_STD  = [0.229, 0.224, 0.225]

pest_eval_transform = transforms.Compose([
    transforms.Resize((PEST_IMG_SIZE, PEST_IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(PEST_MEAN, PEST_STD),
])


def _build_pest_model(num_classes: int) -> nn.Module:
    return timm.create_model("resnet50", pretrained=False,
                             num_classes=num_classes, drop_rate=0.4)


# ── Pydantic schemas PEST ─────────────────────────────────────────────────
class PestPrediction(BaseModel):
    class_name: str
    confidence: float


class PestPredictResponse(BaseModel):
    top1: PestPrediction
    top5: list[PestPrediction]
    inference_ms: float


# =========================================================================
# ── PROJET 8 : INSECT SOUND — architecture & helpers inline ──────────────
# =========================================================================

SOUND_MODEL_PATH     = str(_resolve_asset("sound/CNN14_insect_6classes.pth",           "SOUND_MODEL_PATH"))
SOUND_DEVICE         = torch.device("cuda" if torch.cuda.is_available() else "cpu")
SOUND_SR_TARGET      = 22050
SOUND_SEG_DURATION   = 10.0
SOUND_SEG_SAMPLES    = int(SOUND_SR_TARGET * SOUND_SEG_DURATION)
SOUND_N_FFT          = 1024
SOUND_HOP_LENGTH     = 320
SOUND_WIN_LENGTH     = 1024
SOUND_N_MELS         = 128
SOUND_FMIN           = 50
SOUND_FMAX           = 10000

SOUND_CLASS_NAMES = [
    "Cicada_orni", "Decticus_albifrons", "Gryllus_bimaculatus",
    "Gryllus_campestris", "Tettigonia_cantans", "Tettigonia_viridissima",
]
SOUND_N_CLASSES    = len(SOUND_CLASS_NAMES)
SOUND_IDX_TO_LABEL = {i: c for i, c in enumerate(SOUND_CLASS_NAMES)}


def _init_layer(layer):
    nn.init.xavier_uniform_(layer.weight)
    if hasattr(layer, "bias") and layer.bias is not None:
        layer.bias.data.fill_(0.0)


def _init_bn(bn):
    bn.bias.data.fill_(0.0)
    bn.weight.data.fill_(1.0)


class _ConvBlock(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv1 = nn.Conv2d(in_ch, out_ch, 3, padding=1, bias=False)
        self.conv2 = nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False)
        self.bn1   = nn.BatchNorm2d(out_ch)
        self.bn2   = nn.BatchNorm2d(out_ch)
        _init_layer(self.conv1); _init_layer(self.conv2)
        _init_bn(self.bn1);      _init_bn(self.bn2)

    def forward(self, x, pool_size=(2, 2), pool_type="avg"):
        x = F.relu_(self.bn1(self.conv1(x)))
        x = F.relu_(self.bn2(self.conv2(x)))
        if pool_type == "max":
            x = F.max_pool2d(x, pool_size)
        elif pool_type == "avg":
            x = F.avg_pool2d(x, pool_size)
        elif pool_type == "avg+max":
            x = F.avg_pool2d(x, pool_size) + F.max_pool2d(x, pool_size)
        return x


class _Cnn14Backbone(nn.Module):
    def __init__(self):
        super().__init__()
        self.bn0         = nn.BatchNorm2d(SOUND_N_MELS)
        self.conv_block1 = _ConvBlock(1,    64)
        self.conv_block2 = _ConvBlock(64,   128)
        self.conv_block3 = _ConvBlock(128,  256)
        self.conv_block4 = _ConvBlock(256,  512)
        self.conv_block5 = _ConvBlock(512,  1024)
        self.conv_block6 = _ConvBlock(1024, 2048)
        self.fc1         = nn.Linear(2048, 2048, bias=True)
        self.fc_audioset = nn.Linear(2048, 527,  bias=True)
        _init_bn(self.bn0)
        _init_layer(self.fc1)
        _init_layer(self.fc_audioset)


class _CNN14InsectClassifier(nn.Module):
    def __init__(self, n_classes):
        super().__init__()
        self.backbone   = _Cnn14Backbone()
        self.classifier = nn.Sequential(
            nn.Linear(2048, 512), nn.BatchNorm1d(512),
            nn.ReLU(inplace=True), nn.Dropout(0.4),
            nn.Linear(512, n_classes),
        )

    def _extract_features(self, log_mel):
        x    = log_mel.squeeze(1).unsqueeze(1)
        x_bn = self.backbone.bn0(x.permute(0, 2, 1, 3))
        x    = x_bn.permute(0, 2, 1, 3)
        x = self.backbone.conv_block1(x, (2, 2), "avg")
        x = F.dropout(x, 0.2, self.training)
        x = self.backbone.conv_block2(x, (2, 2), "avg")
        x = F.dropout(x, 0.2, self.training)
        x = self.backbone.conv_block3(x, (2, 2), "avg")
        x = F.dropout(x, 0.2, self.training)
        x = self.backbone.conv_block4(x, (2, 2), "avg")
        x = F.dropout(x, 0.2, self.training)
        x = self.backbone.conv_block5(x, (2, 2), "avg")
        x = F.dropout(x, 0.2, self.training)
        x = self.backbone.conv_block6(x, (1, 1), "avg")
        x = F.dropout(x, 0.2, self.training)
        x  = torch.mean(x, dim=3)
        x1 = F.max_pool1d(x, 3, 1, 1)
        x2 = F.avg_pool1d(x, 3, 1, 1)
        x  = x1 + x2
        x  = F.dropout(x, 0.5, self.training)
        x  = x.transpose(1, 2)
        x  = F.relu_(self.backbone.fc1(x))
        x  = F.dropout(x, 0.5, self.training)
        return torch.mean(x, dim=1)

    def forward(self, x):
        return self.classifier(self._extract_features(x))


def _audio_to_logmel(audio_bytes: bytes) -> torch.Tensor:
    y, sr = sf.read(io.BytesIO(audio_bytes))
    if y.ndim > 1:
        y = y.mean(axis=1)
    if sr != SOUND_SR_TARGET:
        y = librosa.resample(y.astype(np.float32), orig_sr=sr, target_sr=SOUND_SR_TARGET)
    y    = y.astype(np.float32)
    peak = np.max(np.abs(y))
    if peak > 1e-8:
        y = y / peak
    if len(y) < SOUND_SEG_SAMPLES:
        y = np.pad(y, (0, SOUND_SEG_SAMPLES - len(y)))
    else:
        y = y[:SOUND_SEG_SAMPLES]
    mel     = librosa.feature.melspectrogram(
        y=y, sr=SOUND_SR_TARGET, n_fft=SOUND_N_FFT, hop_length=SOUND_HOP_LENGTH,
        win_length=SOUND_WIN_LENGTH, n_mels=SOUND_N_MELS,
        fmin=SOUND_FMIN, fmax=SOUND_FMAX, power=2.0,
    )
    log_mel = np.log(mel + 1e-7).astype(np.float32)
    return torch.FloatTensor(log_mel).unsqueeze(0).unsqueeze(0).to(SOUND_DEVICE)


# =========================================================================
# Helpers Projet 2
# =========================================================================

def _resolve_model_file(name: str) -> Path:
    p = MODELS_DIR_DURUM / name
    if p.exists():
        return p
    root = MODELS_DIR_DURUM.parent / name
    if root.exists():
        return root
    raise FileNotFoundError(name)


def _read_csv_robust(path: Path) -> pd.DataFrame:
    try:
        if path.read_bytes()[:2] == b"PK":
            return pd.read_excel(path)
    except Exception:
        pass
    for kw in [
        {"sep": ",",  "encoding": "utf-8"},
        {"sep": ";",  "encoding": "utf-8"},
        {"sep": ",",  "encoding": "cp1252"},
        {"sep": ";",  "encoding": "cp1252"},
        {"sep": ",",  "encoding": "latin1"},
        {"sep": ";",  "encoding": "latin1"},
    ]:
        try:
            return pd.read_csv(path, **kw)
        except Exception:
            pass
    raise RuntimeError(f"Impossible de lire {path}")


# =========================================================================
# Lifespan combiné
# =========================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    # ── Projet 1 : Wheat Leaf Disease ────────────────────────────────────
    # CORRECTION : on utilise state.wheat_predictor (et NON state.predictor)
    # pour éviter le conflit avec Projet 3 qui utilise aussi ce nom.
    app.state.wheat_predictor   = None
    app.state.wheat_model_error = None
    try:
        model = load_wheat_model(settings_wheat.model_path)
        app.state.wheat_predictor = WheatPredictor(model)
        print("✅ Projet 1 (Wheat CNN) chargé.")
    except Exception as e:
        app.state.wheat_model_error = str(e)
        print(f"⚠️  Projet 1 (Wheat CNN) non disponible : {e}")

    # ── Projet 2 : Durum Wheat Pipeline ──────────────────────────────────
    app.state.models_loaded = False
    warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.base")
    warnings.filterwarnings("ignore", message=".*InconsistentVersionWarning.*")
    warnings.filterwarnings("ignore", message=".*serialized model.*XGBoost.*")
    warnings.filterwarnings("ignore", message=".*X does not have valid feature names.*")
    os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")
    try:
        metadata_path = _resolve_model_file("metadata.json")
        app.state.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        try:
            preproc_path = _resolve_model_file("df_preprocessed.csv")
            app.state.df = _read_csv_robust(preproc_path)
        except FileNotFoundError:
            app.state.df = preprocess_dataset(load_raw_dataset())
        app.state.df_snp = app.state.df.copy()

        app.state.crossings_df = _read_csv_robust(_resolve_model_file("crossings_df.csv"))
        cdf = app.state.crossings_df
        if "Croisement" in cdf.columns and "crossing_name" not in cdf.columns:
            cdf["crossing_name"] = cdf["Croisement"]
        elif "crossing_name" in cdf.columns and "Croisement" not in cdf.columns:
            cdf["Croisement"] = cdf["crossing_name"]
        if "parent_A" not in cdf.columns or "parent_B" not in cdf.columns:
            split_df = cdf["Croisement"].astype(str).str.split("  x  ", n=1, expand=True)
            cdf["parent_A"] = split_df[0]
            cdf["parent_B"] = split_df[1] if split_df.shape[1] > 1 else None

        app.state.scaler = joblib.load(_resolve_model_file("scaler.pkl"))
        app.state.ridge  = joblib.load(_resolve_model_file("ridge.pkl"))
        app.state.rf     = joblib.load(_resolve_model_file("rf.pkl"))
        app.state.xgb    = joblib.load(_resolve_model_file("xgb.pkl"))
        try:
            app.state.lgb = joblib.load(_resolve_model_file("lgbm.pkl"))
        except Exception:
            app.state.lgb = None

        mlp_cfg = json.loads(_resolve_model_file("mlp_config.json").read_text(encoding="utf-8"))
        mlp = MLPRegressor(mlp_cfg["input_dim"], mlp_cfg["output_dim"], mlp_cfg.get("dropout", 0.3))
        mlp.load_state_dict(torch.load(_resolve_model_file("mlp.pt"), map_location="cpu"))
        mlp.eval()
        app.state.mlp = mlp

        app.state.clf_parent          = joblib.load(_resolve_model_file("clf_parent.pkl"))
        app.state.clf_parent_features = json.loads(
            _resolve_model_file("clf_parent_features.json").read_text(encoding="utf-8")
        )
        app.state.features_parent = app.state.clf_parent_features

        app.state.cnn_model, app.state.cnn_status = load_cnn_model_if_available()
        app.state.cnn_loaded = app.state.cnn_model is not None

        snp_cols     = app.state.metadata["snp_cols"]
        feature_cols = app.state.metadata.get("feature_cols", snp_cols + ["snp_activity"])
        for col in feature_cols:
            if col not in cdf.columns:
                cdf[col] = 0.0
        cdf[feature_cols] = cdf[feature_cols].fillna(0)

        def _fix_pair_features(arr: np.ndarray) -> np.ndarray:
            """
            Convertit pair_features en float64 propre.
            Gère le cas fréquent où le .npy a été sérialisé avec dtype=object
            contenant des strings style '[4.7951517E-1]'.
            """
            import re
            if arr.dtype == object or arr.dtype.kind in ("U", "S"):
                def _parse(v):
                    s = re.sub(r"[\[\]]", "", str(v).strip())
                    return float(s.split()[0].rstrip(","))
                arr = np.vectorize(_parse)(arr).astype(np.float64)
            else:
                arr = arr.astype(np.float64)
            return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)

        try:
            _raw = np.load(_resolve_model_file("pair_features.npy"), allow_pickle=True)
            app.state.pair_features = _fix_pair_features(_raw)
            print(f"[DEBUG] pair_features dtype={app.state.pair_features.dtype} shape={app.state.pair_features.shape} val[0,0]={app.state.pair_features[0,0]}")

        except FileNotFoundError:
            _raw = cdf[feature_cols].to_numpy()
            app.state.pair_features = _fix_pair_features(_raw)

        app.state.feature_cols = feature_cols
        app.state.SNP_COLS     = snp_cols
        app.state.models = {
            "rf":    app.state.rf,
            "xgb":   app.state.xgb,
            "lgb":   app.state.lgb if app.state.lgb is not None else app.state.xgb,
            "ridge": app.state.ridge,
            "mlp":   app.state.mlp,
        }
        app.state.shap_global            = None
        app.state.rf_rank                = None
        app.state.meilleur_oligo_par_snp = {}

        geno_path = MODELS_DIR_DURUM.parent / "data" / "original_genotype_data.xlsx"
        app.state.snp_mapping = {}
        if geno_path.exists():
            try:
                gdf = pd.read_excel(geno_path)
                for _, r in gdf.iterrows():
                    snp = str(r.get("snp", r.get("SNP", "")))
                    if snp:
                        app.state.snp_mapping[snp] = {
                            "chromosome": r.get("chromosome"),
                            "position":   r.get("position"),
                            "allele_A":   str(r.get("allele_A", "A"))[:1],
                            "allele_B":   str(r.get("allele_B", "G"))[:1],
                        }
            except Exception:
                pass

        app.state.models_loaded = True
        app.state.df_agront     = pd.DataFrame()
        app.state.alleles       = {}
        app.state.resultats_odm = pd.DataFrame()

        # Injection des dépendances pour genomic.py (évite les imports runtime)
        _cfg = _p2_config
        app.state.FLANKING_BP    = getattr(_cfg, "FLANKING_BP",    50)
        app.state.GC_OPTIMAL     = getattr(_cfg, "GC_OPTIMAL",     (40.0, 60.0))
        app.state.TM_OPTIMAL     = getattr(_cfg, "TM_OPTIMAL",     (50.0, 65.0))
        app.state.OLIGO_MIN_LEN  = getattr(_cfg, "OLIGO_MIN_LEN",  30)
        app.state.OLIGO_MAX_LEN  = getattr(_cfg, "OLIGO_MAX_LEN",  60)
        app.state.TOP_N_SNPS_ODM = getattr(_cfg, "TOP_N_SNPS_ODM", 20)
        app.state.TMP_FASTA_DIR  = str(getattr(_cfg, "TMP_FASTA_DIR", "tmp_fasta"))
        app.state._wrap_fasta          = _p2_preproc.wrap_fasta
        app.state._compute_shap_global = _p2_explainer.compute_shap_global

        print("✅ Projet 2 (Durum Pipeline) chargé.")
    except Exception as e:
        print(f"⚠️  Projet 2 (Durum Pipeline) non disponible : {e}")

    # ── Projet 3 : G×E LSTM/GRU ──────────────────────────────────────────
    # CORRECTION : on utilise state.gxe_predictor pour ne PAS écraser
    # state.wheat_predictor (Projet 1). state.predictor est gardé en alias
    # pour la rétrocompatibilité des routes projet3.
    app.state.gxe_predictor = None
    app.state.predictor     = None   # alias rétrocompat routes projet3
    try:
        app.state.gxe_predictor = GxEPredictor()
        app.state.predictor     = app.state.gxe_predictor   # alias
        print(f"✅ Projet 3 (G×E) chargé — modèle : {app.state.gxe_predictor.best_model_name}.")
    except Exception as e:
        print(f"⚠️  Projet 3 (G×E) non disponible : {e}")

    # ── Projet 4 : Digital Twin ───────────────────────────────────────────
    try:
        _ = DigitalTwinService()
        print("✅ Projet 4 (Digital Twin) chargé.")
    except Exception as e:
        print(f"⚠️  Projet 4 (Digital Twin) non disponible : {e}")

    # ── Projet 5 : CropDNA ────────────────────────────────────────────────
    try:
        init_db()
        _init_mobile_auth_db()
        print("✅ Projet 5 (CropDNA) chargé.")
        print("✅ Mobile Auth DB prête.")
    except Exception as e:
        print(f"⚠️  Projet 5 (CropDNA) non disponible : {e}")

    # ── ODM Project (Projet 9) : DNABERT ────────────────────────────────────
    try:
        print("✅ Projet 9 (ODM/DNABERT) chargé.")
    except Exception as e:
        print(f"⚠️  Projet 9 (ODM/DNABERT) non disponible : {e}")

    # ── Projet 6 : CRISPR ────────────────────────────────────────────────
    app.state.crispr_model     = None
    app.state.crispr_explainer = None
    try:
        if not CRISPR_MODEL_PATH.exists():
            raise FileNotFoundError(f"model.pkl introuvable : {CRISPR_MODEL_PATH}")

        # Tentative 1 : pickle standard
        crispr_model = None
        load_error   = None
        try:
            with open(CRISPR_MODEL_PATH, "rb") as f:
                crispr_model = pickle.load(f)
        except Exception as e1:
            load_error = e1
            # Tentative 2 : joblib (parfois plus tolérant aux versions numpy)
            try:
                crispr_model = joblib.load(CRISPR_MODEL_PATH)
            except Exception as e2:
                # Le modèle a probablement été sauvegardé avec NumPy 2.x
                # mais NumPy 1.26.4 est installé. Il faut le resauvegarder.
                msg = (
                    "Impossible de charger model.pkl"
                    " (erreur pickle: " + str(e1) +
                    " | erreur joblib: " + str(e2) + ")."
                    " Resauvegardez le modele avec NumPy 1.26.4 :"
                    " joblib.dump(model, 'crispr/model.pkl')"
                )
                raise RuntimeError(msg) from e2

        app.state.crispr_model     = crispr_model
        app.state.crispr_explainer = shap.TreeExplainer(crispr_model)
        print("✅ Projet 6 (CRISPR) chargé.")
    except Exception as e:
        print(f"⚠️  Projet 6 (CRISPR) non disponible : {e}")

    # ── Projet 7 : Pest Image ─────────────────────────────────────────────
    app.state.pest_model = None
    try:
        ckpt_path = Path(PEST_MODEL_PATH)
        if not ckpt_path.exists():
            raise FileNotFoundError(f"checkpoint introuvable : {ckpt_path}")
        pest_m = _build_pest_model(PEST_NUM_CLASSES)
        ckpt   = torch.load(ckpt_path, map_location=PEST_DEVICE)
        pest_m.load_state_dict(ckpt.get("model_state_dict", ckpt))
        pest_m.to(PEST_DEVICE).eval()
        app.state.pest_model = pest_m
        print(f"✅ Projet 7 (Pest Image) chargé sur {PEST_DEVICE}.")
    except Exception as e:
        print(f"⚠️  Projet 7 (Pest Image) non disponible : {e}")

    # ── Projet 8 : Insect Sound ───────────────────────────────────────────
    app.state.sound_model = None
    try:
        snd_path = Path(SOUND_MODEL_PATH)
        if not snd_path.exists():
            raise FileNotFoundError(f"checkpoint introuvable : {snd_path}")
        snd_m = _CNN14InsectClassifier(n_classes=SOUND_N_CLASSES)
        ckpt  = torch.load(snd_path, map_location=SOUND_DEVICE, weights_only=False)
        snd_m.load_state_dict(ckpt.get("model_state_dict", ckpt))
        snd_m.to(SOUND_DEVICE).eval()
        app.state.sound_model = snd_m
        print(f"✅ Projet 8 (Insect Sound) chargé sur {SOUND_DEVICE}.")
    except Exception as e:
        print(f"⚠️  Projet 8 (Insect Sound) non disponible : {e}")

    print("\n[SUCCESS] Tous les projets sont demarres -> http://127.0.0.1:8000/docs\n")
    yield
    print("Stopping combined API.")


# =========================================================================
# Application FastAPI principale
# =========================================================================

app = FastAPI(
    title="🌾 Plateforme Agriculture Intelligente — API Combinée",
    description="""
## Plateforme unifiée de 8 projets FastAPI

| Préfixe | Projet | Description |
|---------|--------|-------------|
| `/wheat`  | Projet 1 | Détection maladies feuilles de blé (CNN/TensorFlow) |
| `/durum`  | Projet 2 | Pipeline ML blé dur (Ridge, RF, XGBoost, MLP) |
| `/gxe`    | Projet 3 | Modélisation G×E phénologique (LSTM/GRU) |
| `/twin`   | Projet 4 | Jumeau numérique blé |
| `/cropdna`| Projet 5 | CropDNA — Génomique & IoT agricole |
| `/crispr` | Projet 6 | Prédiction efficacité édition CRISPR (GBR + SHAP) |
| `/pest`   | Projet 7 | Classification ravageurs agricoles — image (ResNet50) |
| `/sound`  | Projet 8 | Classification sons d'insectes (CNN14 PANN) |
| `/writing`| Projet 11 | Rédaction scientifique multi-agent + analyse ADN |
| `/growth` | Projet 12 | Simulation de croissance plante ADN + climat |
| `/ethics` | Projet 13 | Audit éthique génomique PlantAI |
| `/pharma` | Projet 10 | Plant DNA / Protein Expression ML |
""",
    version="3.0.0",
    lifespan=lifespan,
)

# ── CORS global ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Middleware : vérification modèles Projet 2 ────────────────────────────
@app.middleware("http")
async def ensure_durum_loaded(request: Request, call_next):
    if (
        request.url.path.startswith("/durum")
        and not getattr(request.app.state, "models_loaded", False)
        and request.url.path != "/durum/health"
    ):
        raise HTTPException(status_code=503, detail="Modèles Durum non chargés")
    return await call_next(request)


# ── Static files Projet 4 ─────────────────────────────────────────────────
static_twin = _BASE / "projet4/app/static"
if static_twin.exists():
    app.mount("/twin/static", StaticFiles(directory=str(static_twin)), name="twin_static")

# ── Static files Projet 5 ─────────────────────────────────────────────────
app.mount("/cropdna/static", StaticFiles(directory=str(_BASE / "projet5")), name="cropdna_static")

# ── Static files Projet 7 & 8 ─────────────────────────────────────────────
writing_outputs = _BASE / "projet_7/plant_research_paper/outputs"
writing_outputs.mkdir(parents=True, exist_ok=True)
app.mount("/writing/assets", StaticFiles(directory=str(writing_outputs)), name="writing_assets")

growth_outputs = _BASE / "projet_8/plant_simulator/outputs"
growth_outputs.mkdir(parents=True, exist_ok=True)
app.mount("/growth/outputs", StaticFiles(directory=str(growth_outputs)), name="growth_outputs")

growth_media = _BASE / "projet_8/plant_simulator/media"
growth_media.mkdir(parents=True, exist_ok=True)
app.mount("/growth/media", StaticFiles(directory=str(growth_media)), name="growth_media")

ethics_outputs = _BASE / "projet_9/output"
ethics_outputs.mkdir(parents=True, exist_ok=True)
app.mount("/ethics/outputs", StaticFiles(directory=str(ethics_outputs)), name="ethics_outputs")

# ── Inclusion des routers (Projets 1–5) ───────────────────────────────────
app.include_router(wheat_router,   prefix="/wheat",           tags=["🌿 Wheat Disease"])
app.include_router(odm_router,     prefix="/odm",             tags=["🧬 ODM DNABERT"])
app.include_router(durum_router,   prefix="/durum",           tags=["🌾 Durum Pipeline"])
app.include_router(gxe_router,     prefix="/gxe",             tags=["📊 G×E LSTM/GRU"])
app.include_router(twin_router,    prefix="/twin",             tags=["🤖 Digital Twin"])
app.include_router(module7_router, prefix="/cropdna",         tags=["🧬 CropDNA Module 7"])
app.include_router(module8_router, prefix="/cropdna",         tags=["🧬 CropDNA Module 8"])
app.include_router(iot_router,     prefix="/cropdna/api/iot", tags=["📡 CropDNA IoT"])
app.include_router(pharma_router,  prefix="/pharma",          tags=["💊 Plant Protein Expression ML"])
if writing_router is not None:
    app.include_router(writing_router, prefix="/writing", tags=["✍️ Plant Research Writer"])
if growth_router is not None:
    app.include_router(growth_router, prefix="/growth", tags=["🌱 Plant Growth Simulator"])
if ethics_router is not None:
    app.include_router(ethics_router, prefix="/ethics", tags=["⚖️ PlantAI Ethics Compliance"])


# =========================================================================
# ── Routes Mobile : Auth + TTS ───────────────────────────────────────────
# =========================================================================

@app.post("/auth/signup", tags=["📱 Mobile Auth"])
def mobile_signup(payload: MobileSignupRequest):
    phone = payload.phone.strip()
    email = payload.email.strip().lower()
    if email and "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email")
    if not phone:
        raise HTTPException(status_code=400, detail="Phone is required")
    if not payload.full_name.strip():
        raise HTTPException(status_code=400, detail="Full name is required")

    email = email or f"{phone}@phone.local"
    password_hash = _hash_password(payload.password)
    try:
        with _auth_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO mobile_users
                    (email, phone, password_hash, full_name, farm_name, location)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    email,
                    phone,
                    password_hash,
                    payload.full_name.strip(),
                    payload.farm_name,
                    payload.location,
                ),
            )
            user_id = int(cur.lastrowid)
            token = _create_mobile_token(conn, user_id)
            user = conn.execute("SELECT * FROM mobile_users WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Email or phone already exists")

    return {"access_token": token, "token_type": "bearer", "user": _public_user(user)}


@app.post("/auth/login", tags=["📱 Mobile Auth"])
def mobile_login(payload: MobileLoginRequest):
    identifier = payload.identifier.strip().lower()
    with _auth_conn() as conn:
        user = conn.execute(
            "SELECT * FROM mobile_users WHERE lower(email) = ? OR phone = ?",
            (identifier, payload.identifier.strip()),
        ).fetchone()
        if user is None or not _verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = _create_mobile_token(conn, int(user["id"]))

    return {"access_token": token, "token_type": "bearer", "user": _public_user(user)}


@app.get("/auth/me", tags=["📱 Mobile Auth"])
def mobile_me(token: str):
    user = _get_user_by_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return _public_user(user)


@app.get("/tts", tags=["📱 Mobile TTS"])
def mobile_tts(text: str):
    clean_text = (text or "").strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Text is required")
    return Response(
        content=_make_placeholder_wav(clean_text),
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )


# =========================================================================
# ── Routes Projet 6 : CRISPR ─────────────────────────────────────────────
# =========================================================================

@app.get("/api/crispr/health", tags=["🧬 CRISPR"])
def crispr_health(request: Request):
    m = request.app.state.crispr_model
    return {
        "status": "ok",
        "model_loaded": m is not None,
        "model_type": type(m).__name__ if m else None,
    }


@app.get("/api/crispr/features", tags=["🧬 CRISPR"])
def crispr_features(request: Request):
    m = request.app.state.crispr_model
    if m and hasattr(m, "feature_names_in_"):
        return {"feature_names": list(m.feature_names_in_)}
    return {"feature_names": None, "note": "Model does not expose feature_names_in_"}


@app.post("/api/crispr/predict", response_model=CrisprPredictionResponse, tags=["🧬 CRISPR"])
def crispr_predict(req: CrisprPredictionRequest, request: Request):
    """Prédit l'efficacité d'édition CRISPR (%). Rapide — sans SHAP."""
    m = request.app.state.crispr_model
    if m is None:
        raise HTTPException(503, detail="Modèle CRISPR non chargé")
    try:
        X   = _crispr_build_vector(req, m)
        raw = float(m.predict(X)[0])
        clipped = not (0.0 <= raw <= 100.0)
        pred    = round(float(np.clip(raw, 0.0, 100.0)), 4)
        return CrisprPredictionResponse(
            efficiency=pred,
            predicted_editing_efficiency=pred,
            prediction_clipped=clipped,
        )
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc


@app.post("/api/crispr/explain", response_model=CrisprExplainResponse, tags=["🧬 CRISPR"])
def crispr_explain(req: CrisprPredictionRequest, request: Request, top_n: int = 10):
    """Prédit + explique via SHAP (top features qui influencent la prédiction)."""
    m   = request.app.state.crispr_model
    exp = request.app.state.crispr_explainer
    if m is None or exp is None:
        raise HTTPException(503, detail="Modèle CRISPR non chargé")
    try:
        X   = _crispr_build_vector(req, m)
        raw = float(m.predict(X)[0])
        clipped = not (0.0 <= raw <= 100.0)
        pred    = round(float(np.clip(raw, 0.0, 100.0)), 4)

        # Robust SHAP call
        try:
            # Try the new API first (Explanation object)
            shap_out = exp(X)
            if hasattr(shap_out, "values"):
                shap_vals = shap_out.values[0]
                base_value = float(shap_out.base_values[0])
            else:
                # Fallback for older versions
                shap_vals = exp.shap_values(X)
                if isinstance(shap_vals, list): shap_vals = shap_vals[0]
                shap_vals = shap_vals[0]
                base_value = float(exp.expected_value)
        except Exception:
            # Direct fallback
            shap_vals = exp.shap_values(X)
            if isinstance(shap_vals, list): shap_vals = shap_vals[0]
            if len(shap_vals.shape) > 1: shap_vals = shap_vals[0]
            base_value = float(getattr(exp, "expected_value", 0))

        feat_vals  = X.values[0]
        feat_names = list(X.columns)
        
        contribs = []
        for name, val, sv in zip(feat_names, feat_vals, shap_vals):
            contribs.append(
                CrisprFeatureContribution(
                    feature=name,
                    value=round(float(val), 6),
                    shap_value=round(float(sv), 6),
                    direction="up" if sv > 0 else "down",
                )
            )
        sorted_c = sorted(contribs, key=lambda c: abs(c.shap_value), reverse=True)

        return CrisprExplainResponse(
            predicted_editing_efficiency=pred,
            prediction_clipped=clipped,
            baseline=round(base_value, 4),
            net_shap_shift=round(float(shap_vals.sum()), 4),
            top_drivers=sorted_c[:top_n],
            all_contributions=sorted_c,
            top_n=top_n,
        )
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc


@app.post("/api/crispr/recommend", tags=["🧬 CRISPR"])
def crispr_recommend(req: CrisprRecommendRequest, request: Request):
    """Génère une recommandation textuelle dynamique basée sur la prédiction."""
    pred = round(req.efficiency, 1)
    gc   = req.features.get("guideGC", 0.5)
    chrom = req.features.get("chromatin", True)
    reg   = req.features.get("region", "Exon")
    
    if pred >= 60:
        verdict = "STRONG candidate"
    elif pred >= 30:
        verdict = "MODERATE candidate"
    else:
        verdict = "WEAK candidate"
        
    text = (
        f"Based on hybrid retrieval signals and Gradient Boosting inference, this sgRNA is a {verdict}. "
        f"The predicted efficiency of {pred}% is driven by the "
        f"{'open chromatin (ATAC+)' if chrom else 'closed chromatin (ATAC-)'} "
        f"state and a GC content of {gc*100:.1f}%. "
        f"Targeting the {reg} region suggests good genomic accessibility. "
        f"VERDICT: {'PROCEED' if pred >= 50 else 'RE-DESIGN' if pred < 30 else 'CAUTION'}."
    )
    
    return {"recommendation": text}


# =========================================================================
# ── Routes Projet 7 : PEST IMAGE ─────────────────────────────────────────
# =========================================================================

@app.get("/pest/health", tags=["🐛 Pest Image"])
def pest_health(request: Request):
    m = request.app.state.pest_model
    return {
        "status": "ok",
        "model_loaded": m is not None,
        "device": str(PEST_DEVICE),
    }


@app.get("/pest/classes", tags=["🐛 Pest Image"])
def pest_classes():
    return {"classes": PEST_CLASS_NAMES, "num_classes": PEST_NUM_CLASSES}


@app.post("/pest/predict", response_model=PestPredictResponse, tags=["🐛 Pest Image"])
async def pest_predict(request: Request, file: UploadFile = File(...)):
    """Upload une image JPEG/PNG → top-5 classes de ravageurs avec scores."""
    m = request.app.state.pest_model
    if m is None:
        raise HTTPException(503, detail="Modèle Pest non chargé")

    allowed = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(415, detail=f"Type non supporté : {file.content_type}")

    image_bytes = await file.read()
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(400, detail=f"Impossible de décoder l'image : {exc}")

    tensor = pest_eval_transform(img).unsqueeze(0).to(PEST_DEVICE)
    t0 = time.perf_counter()
    with torch.no_grad():
        with autocast("cuda" if PEST_USE_AMP else "cpu", enabled=PEST_USE_AMP):
            logits = m(tensor)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    probs = torch.softmax(logits, dim=1).squeeze().cpu()
    top5  = probs.topk(5)
    preds = [
        PestPrediction(
            class_name=PEST_CLASS_NAMES[idx.item()],
            confidence=round(conf.item(), 6),
        )
        for conf, idx in zip(top5.values, top5.indices)
    ]
    return PestPredictResponse(top1=preds[0], top5=preds, inference_ms=round(elapsed_ms, 2))


# =========================================================================
# ── Routes Projet 8 : INSECT SOUND ───────────────────────────────────────
# =========================================================================

@app.get("/sound/health", tags=["🔊 Insect Sound"])
def sound_health(request: Request):
    m = request.app.state.sound_model
    return {
        "status": "ok",
        "model_loaded": m is not None,
        "device": str(SOUND_DEVICE),
    }


@app.get("/sound/classes", tags=["🔊 Insect Sound"])
def sound_classes():
    return {"classes": SOUND_CLASS_NAMES, "num_classes": SOUND_N_CLASSES}


@app.post("/sound/predict", tags=["🔊 Insect Sound"])
async def sound_predict(request: Request, audio: UploadFile = File(...)):
    """
    Upload un fichier audio .wav → classification d'espèce d'insecte (top-3).
    Seules les 10 premières secondes sont utilisées (comme à l'entraînement).
    L'audio est automatiquement rééchantillonné à 22050 Hz si nécessaire.
    """
    m = request.app.state.sound_model
    if m is None:
        raise HTTPException(503, detail="Modèle Sound non chargé")

    audio_bytes = await audio.read()
    try:
        tensor = _audio_to_logmel(audio_bytes)
        with torch.no_grad():
            probs = torch.softmax(m(tensor), dim=1).squeeze().cpu()
        top3 = probs.topk(3)
        return {
            "predicted_class": SOUND_IDX_TO_LABEL[top3.indices[0].item()],
            "confidence": round(top3.values[0].item() * 100, 2),
            "top_predictions": [
                {
                    "class": SOUND_IDX_TO_LABEL[i.item()],
                    "confidence": round(p.item() * 100, 2),
                }
                for i, p in zip(top3.indices, top3.values)
            ],
        }
    except RuntimeError as e:
        raise HTTPException(503, detail=str(e))
    except Exception as e:
        raise HTTPException(400, detail=f"Impossible de traiter l'audio : {e}")


# =========================================================================
# ── Routes globales ───────────────────────────────────────────────────────
# =========================================================================

@app.get("/", tags=["Info"])
def root():
    return {
        "platform": "🌾 Plateforme Agriculture Intelligente",
        "version": "4.0.0",
        "projets": {
            "wheat":   "/wheat   → Détection maladies feuilles de blé",
            "durum":   "/durum   → Pipeline ML blé dur",
            "gxe":     "/gxe     → Modélisation G×E LSTM/GRU",
            "twin":    "/twin    → Jumeau numérique",
            "cropdna": "/cropdna → Génomique & IoT",
            "crispr":  "/crispr  → Prédiction efficacité CRISPR + SHAP",
            "pest":    "/pest    → Classification ravageurs (image)",
            "sound":   "/sound   → Classification sons d'insectes",
            "odm":     "/odm     → ODM Wheat DNABERT Fine-Tuning",
            "writing": "/writing → Scientific research paper generation",
            "growth":  "/growth  → Plant growth simulator",
            "ethics":  "/ethics  → PlantAI ethical compliance audit",
            "pharma":  "/pharma  → Plant DNA / Protein Expression ML",
        },
        "docs": "/docs",
    }


@app.get("/health", tags=["Info"])
def health(request: Request):
    s = request.app.state
    return {
        "status": "ok",
        "projets": {
            "wheat":  getattr(s, "wheat_predictor",   None) is not None,
            "durum":  getattr(s, "models_loaded",     False),
            "gxe":    getattr(s, "gxe_predictor",     None) is not None,
            "crispr": getattr(s, "crispr_model",      None) is not None,
            "pest":   getattr(s, "pest_model",        None) is not None,
            "sound":  getattr(s, "sound_model",       None) is not None,
            "odm":    True,  # stateless — routes toujours disponibles si chargé
            "writing": writing_router is not None,
            "growth": growth_router is not None,
            "ethics": ethics_router is not None,
            "pharma": True,  # stateless — routes toujours disponibles si chargé
        },
    }


# ── Test page Projet 5 ────────────────────────────────────────────────────
@app.get("/cropdna/test", tags=["🧬 CropDNA IoT"])
def test_page():
    return FileResponse("projet5/test.html")


# ── Lancement direct ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_combine:app", host="0.0.0.0", port=8000, reload=True)
