"""
FastAPI — IP102 Pest Classification (15 Classes)
Model: ResNet50 fine-tuned (timm), trained as in the notebook.
Endpoints:
  POST /predict        — upload an image, get top-5 predictions
  GET  /classes        — list all class names
  GET  /health         — liveness check
"""

import io
import os
import time
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import timm
from PIL import Image
from torchvision import transforms
from torch.amp import autocast

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# ─────────────────────────────────────────────
#  Configuration  (mirrors notebook §2)
# ─────────────────────────────────────────────
IMG_SIZE    = 224
NUM_CLASSES = 15
USE_AMP     = torch.cuda.is_available()   # fp16 only when GPU is present
DEVICE      = torch.device("cuda" if torch.cuda.is_available() else "cpu")

CLASS_NAMES = [
    "army_worm", "asiatic_rice_borer", "beet_army_worm", "blister_beetle",
    "Cicadella_viridis", "Cicadellidae", "corn_borer", "flax_budworm",
    "legume_blister_beetle", "Limacodidae", "Lycorma_delicatula", "Miridae",
    "mole_cricket", "Prodenia_litura", "rice_leaf_roller",
]

# Path to the .pth checkpoint produced by the notebook (§7 / §10).
# Set via env-var MODEL_PATH or fall back to the default notebook output path.
MODEL_PATH = os.getenv(
    "MODEL_PATH",
    "best_efficientnet_b0_ip102.pth",   # place the file next to main.py, or set the env-var
)

MEAN = [0.485, 0.456, 0.406]
STD  = [0.229, 0.224, 0.225]


# ─────────────────────────────────────────────
#  Preprocessing transform  (mirrors notebook §4 eval_tf)
# ─────────────────────────────────────────────
eval_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(MEAN, STD),
])


# ─────────────────────────────────────────────
#  Model builder  (mirrors notebook §5)
# ─────────────────────────────────────────────
def build_model(num_classes: int, dropout: float = 0.4) -> nn.Module:
    model = timm.create_model(
        "resnet50",
        pretrained=False,       # weights come from our checkpoint
        num_classes=num_classes,
        drop_rate=dropout,
    )
    return model


# ─────────────────────────────────────────────
#  Load checkpoint
# ─────────────────────────────────────────────
def load_model(path: str) -> nn.Module:
    model = build_model(NUM_CLASSES)
    ckpt_path = Path(path)
    if not ckpt_path.exists():
        raise FileNotFoundError(
            f"Checkpoint not found at '{ckpt_path.resolve()}'. "
            "Set MODEL_PATH env-var to the correct .pth file."
        )
    checkpoint = torch.load(ckpt_path, map_location=DEVICE)
    # The notebook saves a dict with 'model_state_dict' key (§7 / §10)
    state = checkpoint.get("model_state_dict", checkpoint)
    model.load_state_dict(state)
    model.to(DEVICE)
    model.eval()
    return model


# ─────────────────────────────────────────────
#  FastAPI app
# ─────────────────────────────────────────────
app = FastAPI(
    title="IP102 Pest Classifier",
    description=(
        "Classifies agricultural pest images into 15 categories using a "
        "ResNet50 model trained on the IP102 dataset."
    ),
    version="1.0.0",
)

# Global model handle — loaded once at startup
_model: Optional[nn.Module] = None


@app.on_event("startup")
def startup_event():
    global _model
    try:
        _model = load_model(MODEL_PATH)
        print(f"✅ Model loaded from '{MODEL_PATH}' on {DEVICE}")
    except FileNotFoundError as exc:
        # App starts but /predict will return 503 until model is available
        print(f"⚠️  {exc}")
        _model = None


# ─────────────────────────────────────────────
#  Response schemas
# ─────────────────────────────────────────────
class Prediction(BaseModel):
    class_name: str
    confidence: float   # 0.0 – 1.0


class PredictResponse(BaseModel):
    top1: Prediction
    top5: list[Prediction]
    inference_ms: float


class ClassesResponse(BaseModel):
    classes: list[str]
    num_classes: int


class HealthResponse(BaseModel):
    status: str
    device: str
    model_loaded: bool


# ─────────────────────────────────────────────
#  Helper — run inference  (mirrors notebook §11 predict_image)
# ─────────────────────────────────────────────
def run_inference(image_bytes: bytes) -> PredictResponse:
    if _model is None:
        raise HTTPException(
            status_code=503,
            detail=f"Model not loaded. Check that '{MODEL_PATH}' exists and restart.",
        )

    # Decode image
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot decode image: {exc}")

    tensor = eval_transform(img).unsqueeze(0).to(DEVICE)   # (1, 3, 224, 224)

    t0 = time.perf_counter()
    with torch.no_grad():
        with autocast("cuda" if USE_AMP else "cpu", enabled=USE_AMP):
            logits = _model(tensor)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    probs = torch.softmax(logits, dim=1).squeeze().cpu()    # (15,)
    top5  = probs.topk(5)

    predictions = [
        Prediction(
            class_name=CLASS_NAMES[idx.item()],
            confidence=round(conf.item(), 6),
        )
        for conf, idx in zip(top5.values, top5.indices)
    ]

    return PredictResponse(
        top1=predictions[0],
        top5=predictions,
        inference_ms=round(elapsed_ms, 2),
    )


# ─────────────────────────────────────────────
#  Routes
# ─────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["Utility"])
def health():
    """Liveness check — returns model and device status."""
    return HealthResponse(
        status="ok",
        device=str(DEVICE),
        model_loaded=_model is not None,
    )


@app.get("/classes", response_model=ClassesResponse, tags=["Utility"])
def get_classes():
    """Return all supported pest class names."""
    return ClassesResponse(classes=CLASS_NAMES, num_classes=NUM_CLASSES)


@app.post("/predict", response_model=PredictResponse, tags=["Inference"])
async def predict(file: UploadFile = File(..., description="JPEG or PNG pest image")):
    """
    Upload an image (JPEG / PNG) and receive the top-5 pest class predictions
    with confidence scores.

    - **top1**: single best prediction
    - **top5**: ranked list of 5 predictions
    - **inference_ms**: server-side inference time in milliseconds
    """
    allowed_types = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type '{file.content_type}'. Use JPEG or PNG.",
        )

    image_bytes = await file.read()
    return run_inference(image_bytes)