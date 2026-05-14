import os
import io
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
import librosa
import numpy as np
import soundfile as sf

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ─────────────────────────────────────────────────────────────────────────────
#  Config  (must match training)
# ─────────────────────────────────────────────────────────────────────────────
MODEL_PATH = os.getenv("MODEL_PATH", "best_model.pth")
DEVICE     = torch.device("cuda" if torch.cuda.is_available() else "cpu")

SR_TARGET        = 22050
SEGMENT_DURATION = 10.0
SEGMENT_SAMPLES  = int(SR_TARGET * SEGMENT_DURATION)

N_FFT      = 1024
HOP_LENGTH = 320
WIN_LENGTH = 1024
N_MELS     = 128
FMIN       = 50
FMAX       = 10000

CLASS_NAMES = [
    'Cicada_orni',
    'Decticus_albifrons',
    'Gryllus_bimaculatus',
    'Gryllus_campestris',
    'Tettigonia_cantans',
    'Tettigonia_viridissima',
]
N_CLASSES    = len(CLASS_NAMES)
IDX_TO_LABEL = {i: c for i, c in enumerate(CLASS_NAMES)}

# ─────────────────────────────────────────────────────────────────────────────
#  Model architecture  (identical to notebook)
# ─────────────────────────────────────────────────────────────────────────────
def init_layer(layer):
    nn.init.xavier_uniform_(layer.weight)
    if hasattr(layer, 'bias') and layer.bias is not None:
        layer.bias.data.fill_(0.)

def init_bn(bn):
    bn.bias.data.fill_(0.)
    bn.weight.data.fill_(1.)


class ConvBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, 3, padding=1, bias=False)
        self.conv2 = nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False)
        self.bn1   = nn.BatchNorm2d(out_channels)
        self.bn2   = nn.BatchNorm2d(out_channels)
        init_layer(self.conv1); init_layer(self.conv2)
        init_bn(self.bn1);      init_bn(self.bn2)

    def forward(self, x, pool_size=(2, 2), pool_type='avg'):
        x = F.relu_(self.bn1(self.conv1(x)))
        x = F.relu_(self.bn2(self.conv2(x)))
        if pool_type == 'max':
            x = F.max_pool2d(x, pool_size)
        elif pool_type == 'avg':
            x = F.avg_pool2d(x, pool_size)
        elif pool_type == 'avg+max':
            x = F.avg_pool2d(x, pool_size) + F.max_pool2d(x, pool_size)
        return x


class Cnn14Backbone(nn.Module):
    def __init__(self):
        super().__init__()
        self.bn0         = nn.BatchNorm2d(N_MELS)
        self.conv_block1 = ConvBlock(1,    64)
        self.conv_block2 = ConvBlock(64,   128)
        self.conv_block3 = ConvBlock(128,  256)
        self.conv_block4 = ConvBlock(256,  512)
        self.conv_block5 = ConvBlock(512,  1024)
        self.conv_block6 = ConvBlock(1024, 2048)
        self.fc1         = nn.Linear(2048, 2048, bias=True)
        self.fc_audioset = nn.Linear(2048, 527,  bias=True)
        init_bn(self.bn0)
        init_layer(self.fc1)
        init_layer(self.fc_audioset)


class CNN14InsectClassifier(nn.Module):
    def __init__(self, n_classes):
        super().__init__()
        self.backbone   = Cnn14Backbone()
        self.classifier = nn.Sequential(
            nn.Linear(2048, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),
            nn.Linear(512, n_classes),
        )

    def _extract_features(self, log_mel):
        x    = log_mel.squeeze(1).unsqueeze(1)        # (B, 1, N_MELS, T)
        x_bn = self.backbone.bn0(x.permute(0, 2, 1, 3))
        x    = x_bn.permute(0, 2, 1, 3)

        x = self.backbone.conv_block1(x, (2, 2), 'avg')
        x = F.dropout(x, 0.2, self.training)
        x = self.backbone.conv_block2(x, (2, 2), 'avg')
        x = F.dropout(x, 0.2, self.training)
        x = self.backbone.conv_block3(x, (2, 2), 'avg')
        x = F.dropout(x, 0.2, self.training)
        x = self.backbone.conv_block4(x, (2, 2), 'avg')
        x = F.dropout(x, 0.2, self.training)
        x = self.backbone.conv_block5(x, (2, 2), 'avg')
        x = F.dropout(x, 0.2, self.training)
        x = self.backbone.conv_block6(x, (1, 1), 'avg')
        x = F.dropout(x, 0.2, self.training)

        x  = torch.mean(x, dim=3)
        x1 = F.max_pool1d(x, 3, 1, 1)
        x2 = F.avg_pool1d(x, 3, 1, 1)
        x  = x1 + x2
        x  = F.dropout(x, 0.5, self.training)
        x  = x.transpose(1, 2)
        x  = F.relu_(self.backbone.fc1(x))
        x  = F.dropout(x, 0.5, self.training)
        x  = torch.mean(x, dim=1)
        return x

    def forward(self, x):
        return self.classifier(self._extract_features(x))


# ─────────────────────────────────────────────────────────────────────────────
#  Load model (lazy)
# ─────────────────────────────────────────────────────────────────────────────
_model = None

def get_model() -> CNN14InsectClassifier:
    global _model
    if _model is None:
        if not Path(MODEL_PATH).exists():
            raise RuntimeError(f"Model file not found: {MODEL_PATH}")
        m    = CNN14InsectClassifier(n_classes=N_CLASSES)
        ckpt = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=False)
        m.load_state_dict(ckpt.get("model_state_dict", ckpt))
        m.to(DEVICE).eval()
        _model = m
    return _model


# ─────────────────────────────────────────────────────────────────────────────
#  Audio preprocessing
# ─────────────────────────────────────────────────────────────────────────────
def audio_to_logmel(audio_bytes: bytes) -> torch.Tensor:
    y, sr = sf.read(io.BytesIO(audio_bytes))
    if y.ndim > 1:
        y = y.mean(axis=1)
    if sr != SR_TARGET:
        y = librosa.resample(y.astype(np.float32), orig_sr=sr, target_sr=SR_TARGET)
    y = y.astype(np.float32)
    peak = np.max(np.abs(y))
    if peak > 1e-8:
        y = y / peak
    if len(y) < SEGMENT_SAMPLES:
        y = np.pad(y, (0, SEGMENT_SAMPLES - len(y)))
    else:
        y = y[:SEGMENT_SAMPLES]
    mel = librosa.feature.melspectrogram(
        y=y, sr=SR_TARGET,
        n_fft=N_FFT, hop_length=HOP_LENGTH, win_length=WIN_LENGTH,
        n_mels=N_MELS, fmin=FMIN, fmax=FMAX, power=2.0,
    )
    log_mel = np.log(mel + 1e-7).astype(np.float32)
    return torch.FloatTensor(log_mel).unsqueeze(0).unsqueeze(0).to(DEVICE)


# ─────────────────────────────────────────────────────────────────────────────
#  Inference
# ─────────────────────────────────────────────────────────────────────────────
def run_inference(audio_bytes: bytes) -> dict:
    tensor = audio_to_logmel(audio_bytes)
    with torch.no_grad():
        probs = torch.softmax(get_model()(tensor), dim=1).squeeze().cpu()
    top3 = probs.topk(3)
    return {
        "predicted_class": IDX_TO_LABEL[top3.indices[0].item()],
        "confidence": round(top3.values[0].item() * 100, 2),
        "top_predictions": [
            {"class": IDX_TO_LABEL[i.item()], "confidence": round(p.item() * 100, 2)}
            for i, p in zip(top3.indices, top3.values)
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  FastAPI
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="PANN CNN14 Insect Sound Classifier", version="1.0.0")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/")
def root():
    return {"status": "ok", "model": "CNN14 PANN — 6 insect classes"}


@app.get("/classes")
def list_classes():
    return {"classes": CLASS_NAMES, "num_classes": N_CLASSES}


@app.post("/predict")
async def predict(audio: UploadFile = File(...)):
    """
    Upload a .wav audio file → insect species classification.
    - Only the first 10 seconds are used (matches training).
    - Audio is auto-resampled to 22050 Hz if needed.
    """
    audio_bytes = await audio.read()
    try:
        return run_inference(audio_bytes)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(400, f"Could not process audio: {e}")
